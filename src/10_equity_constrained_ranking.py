"""Optimise top-K selections subject to explicit equity representation floors."""
from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np
import pandas as pd

from utils import OUTPUTS, PROCESSED

K = 20
CONSTRAINTS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
PRIMARY_EQUITY_FLOOR = 0.4
PROVIDER_CAPS = (None, 1, 2, 3)


def constrained_top_k(
    frame: pd.DataFrame,
    score: str,
    k: int,
    minimum_high_need_share: float,
    max_services_per_provider: int | None = None,
) -> pd.DataFrame:
    ranked = frame.sort_values(score, ascending=False).copy()
    required = math.ceil(k * minimum_high_need_share)
    selected_indexes: list[int] = []
    provider_counts: Counter = Counter()

    def add_candidates(candidates: pd.DataFrame, limit: int) -> None:
        for index, row in candidates.iterrows():
            if len(selected_indexes) >= limit:
                break
            if index in selected_indexes:
                continue
            provider = row.provider_code
            if (
                max_services_per_provider is not None
                and provider_counts[provider] >= max_services_per_provider
            ):
                continue
            selected_indexes.append(index)
            provider_counts[provider] += 1

    add_candidates(ranked[ranked.high_equity_need], required)
    add_candidates(ranked, k)
    selected = ranked.loc[selected_indexes].copy()
    if len(selected) != min(k, len(ranked)):
        raise RuntimeError(
            f"Provider cap {max_services_per_provider} cannot produce a top-{k} list"
        )
    if int(selected.high_equity_need.sum()) < required:
        raise RuntimeError("Equity representation floor is infeasible")
    return selected.sort_values(score, ascending=False)


def selection_metrics(all_rows: pd.DataFrame, selected: pd.DataFrame, score: str) -> dict:
    actual_top = set(all_rows.nlargest(min(K, len(all_rows)), "target_breach_52w_rate").index)
    chosen = set(selected.index)
    overlap = len(actual_top & chosen)
    return {
        "selected_n": len(selected),
        "predicted_pressure_sum": selected[score].sum(),
        "observed_pressure_sum": selected.target_breach_52w_rate.sum(),
        "observed_pressure_mean": selected.target_breach_52w_rate.mean(),
        "recall_at_20": overlap / min(K, len(all_rows)),
        "high_equity_need_service_share": selected.high_equity_need.mean(),
        "unique_provider_count": selected.provider_code.nunique(),
        "maximum_services_per_provider": selected.provider_code.value_counts().max(),
        "mean_deprivation_disparity": selected.deprivation_disparity.mean(),
        "mean_ethnicity_disparity": selected.ethnicity_disparity.mean(),
        "mean_age_disparity": selected.age_disparity.mean(),
        "mean_sex_disparity": selected.sex_disparity.mean(),
    }


def percentile(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, method="average").fillna(0.5)


def add_legacy_comparator(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    waiting = (
        0.6 * percentile(result.breach_18w_rate)
        + 0.4 * percentile(result.breach_52w_rate)
    )
    equity = pd.concat(
        [
            percentile(result.deprivation_disparity),
            percentile(result.ethnicity_disparity),
            percentile(result.age_disparity),
            percentile(result.sex_disparity),
        ],
        axis=1,
    ).mean(axis=1)
    operations = pd.concat(
        [
            percentile(result.diagnostic_over_6w_rate),
            percentile(result.bed_occupancy_rate),
            percentile(result.log_cancelled_operations),
        ],
        axis=1,
    ).mean(axis=1)
    result["Legacy composite"] = 0.5 * waiting + 0.3 * equity + 0.2 * operations
    return result


def latest_available_snapshot(
    equity: pd.DataFrame, decision_date: pd.Timestamp
) -> pd.DataFrame:
    candidates = equity[
        pd.to_datetime(equity.available_date).le(pd.Timestamp(decision_date))
    ].copy()
    if candidates.empty:
        raise RuntimeError(f"No WLMDS snapshot was available by {decision_date:%Y-%m-%d}")
    snapshot_date = pd.to_datetime(candidates.snapshot_date).max()
    selected = candidates[pd.to_datetime(candidates.snapshot_date).eq(snapshot_date)].copy()
    if pd.to_datetime(selected.available_date).max() > pd.Timestamp(decision_date):
        raise AssertionError("WLMDS availability date exceeds the decision date")
    return selected


def main() -> None:
    metrics_dir = OUTPUTS / "metrics"
    tables_dir = OUTPUTS / "tables"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    specification = json.loads(
        (metrics_dir / "selected_model.json").read_text(encoding="utf-8")
    )
    selected_model = specification["primary_forecaster"]
    selected_learned_model = specification["selected_learned_model"]
    predictions = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    equity = pd.read_parquet(PROCESSED / "equity_indicators.parquet")
    latest_target = predictions.target_date.max()
    frame = predictions[predictions.target_date == latest_target].copy()
    decision_dates = pd.to_datetime(frame.feature_date).drop_duplicates()
    if len(decision_dates) != 1:
        raise RuntimeError("The policy illustration must have one decision date")
    decision_date = decision_dates.iloc[0]
    equity = latest_available_snapshot(equity, decision_date)
    frame = frame.merge(
        equity.drop(columns=["provider_name"], errors="ignore"),
        on="provider_code",
        how="inner",
        validate="many_to_one",
    )
    frame = add_legacy_comparator(frame)

    rows = []
    selections = []
    for constraint in CONSTRAINTS:
        chosen = constrained_top_k(frame, selected_model, K, constraint)
        chosen = chosen.copy()
        chosen["minimum_high_need_share"] = constraint
        chosen["strategy"] = "Equity-constrained primary forecast"
        chosen["provider_service_cap"] = np.nan
        selections.append(chosen)
        rows.append(
            {
                "strategy": "Equity-constrained primary forecast",
                "minimum_high_need_share": constraint,
                "provider_service_cap": np.nan,
                **selection_metrics(frame, chosen, selected_model),
            }
        )
    for strategy, score in (
        ("Primary forecast only", selected_model),
        ("Selected learned model only", selected_learned_model),
        ("Legacy composite comparator", "Legacy composite"),
    ):
        chosen = frame.nlargest(K, score).copy()
        chosen["minimum_high_need_share"] = np.nan
        chosen["strategy"] = strategy
        chosen["provider_service_cap"] = np.nan
        selections.append(chosen)
        rows.append(
            {
                "strategy": strategy,
                "minimum_high_need_share": np.nan,
                "provider_service_cap": np.nan,
                **selection_metrics(frame, chosen, score),
            }
        )

    tradeoff = pd.DataFrame(rows)
    tradeoff["decision_date"] = pd.Timestamp(decision_date).date().isoformat()
    tradeoff["equity_snapshot_date"] = pd.to_datetime(equity.snapshot_date).max().date().isoformat()
    tradeoff["equity_available_date"] = pd.to_datetime(equity.available_date).max().date().isoformat()
    tradeoff.to_csv(metrics_dir / "equity_pressure_capture_frontier.csv", index=False)

    cap_rows = []
    for cap in PROVIDER_CAPS:
        chosen = constrained_top_k(
            frame,
            selected_model,
            K,
            PRIMARY_EQUITY_FLOOR,
            max_services_per_provider=cap,
        )
        chosen = chosen.copy()
        chosen["minimum_high_need_share"] = PRIMARY_EQUITY_FLOOR
        chosen["strategy"] = "Provider-cap sensitivity"
        chosen["provider_service_cap"] = cap if cap is not None else np.nan
        selections.append(chosen)
        cap_rows.append(
            {
                "provider_service_cap": "unlimited" if cap is None else str(cap),
                "minimum_high_need_share": PRIMARY_EQUITY_FLOOR,
                **selection_metrics(frame, chosen, selected_model),
            }
        )
    pd.DataFrame(cap_rows).to_csv(
        metrics_dir / "provider_cap_sensitivity.csv", index=False
    )
    selected_rows = pd.concat(selections).reset_index(drop=True)
    selected_rows.to_parquet(PROCESSED / "equity_constrained_selections.parquet", index=False)
    selected_rows[
        [
            "strategy",
            "minimum_high_need_share",
            "provider_name",
            "treatment_function_name",
            selected_model,
            "target_breach_52w_rate",
            "high_equity_need",
            "deprivation_disparity",
            "ethnicity_disparity",
            "age_disparity",
            "sex_disparity",
        ]
    ].to_csv(tables_dir / "top20_equity_constrained_selections.csv", index=False)
    print(tradeoff.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
