"""Optimise top-K selections subject to explicit equity representation floors."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from utils import OUTPUTS, PROCESSED

K = 20
CONSTRAINTS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)


def constrained_top_k(
    frame: pd.DataFrame,
    score: str,
    k: int,
    minimum_high_need_share: float,
) -> pd.DataFrame:
    ranked = frame.sort_values(score, ascending=False).copy()
    selected = ranked.head(k).copy()
    required = math.ceil(k * minimum_high_need_share)
    deficit = required - int(selected.high_equity_need.sum())
    if deficit > 0:
        replacements = ranked[
            ranked.high_equity_need & ~ranked.index.isin(selected.index)
        ].head(deficit)
        removable = selected[~selected.high_equity_need].nsmallest(deficit, score)
        selected = pd.concat(
            [selected.drop(index=removable.index), replacements], ignore_index=False
        )
    return selected.sort_values(score, ascending=False).head(k)


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
        "high_equity_need_share": selected.high_equity_need.mean(),
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


def main() -> None:
    metrics_dir = OUTPUTS / "metrics"
    tables_dir = OUTPUTS / "tables"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    selected_model = json.loads(
        (metrics_dir / "selected_model.json").read_text(encoding="utf-8")
    )["selected_model"]
    predictions = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    equity = pd.read_parquet(PROCESSED / "equity_indicators.parquet")
    latest_target = predictions.target_date.max()
    frame = predictions[predictions.target_date == latest_target].copy()
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
        chosen["strategy"] = "Equity-constrained forecast"
        selections.append(chosen)
        rows.append(
            {
                "strategy": "Equity-constrained forecast",
                "minimum_high_need_share": constraint,
                **selection_metrics(frame, chosen, selected_model),
            }
        )
    for strategy, score in (
        ("Persistence", "Persistence"),
        ("Legacy composite comparator", "Legacy composite"),
        ("Forecast risk only", selected_model),
    ):
        chosen = frame.nlargest(K, score).copy()
        chosen["minimum_high_need_share"] = np.nan
        chosen["strategy"] = strategy
        selections.append(chosen)
        rows.append(
            {
                "strategy": strategy,
                "minimum_high_need_share": np.nan,
                **selection_metrics(frame, chosen, score),
            }
        )

    tradeoff = pd.DataFrame(rows)
    tradeoff.to_csv(metrics_dir / "equity_utility_tradeoff.csv", index=False)
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
