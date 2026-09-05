"""Month-level evaluation and provider-cluster bootstrap intervals."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as forecasting  # noqa: E402
from utils import OUTPUTS, PROCESSED  # noqa: E402

BOOTSTRAP_REPLICATES = 100


def model_columns(frame: pd.DataFrame) -> list[str]:
    excluded = set(forecasting.predictor_columns(forecasting.FULL_FEATURES)) | {
        "feature_date",
        "target_date",
        "month",
        "provider_code",
        "provider_name",
        "treatment_function_code",
        "treatment_function_name",
        forecasting.TARGET,
        "target_change_52w",
        "breach_52w_rate",
        "breach_52w_roll3",
    }
    return [column for column in frame.columns if column not in excluded]


def monthly_metrics(frame: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    rows = []
    for target_date, month in frame.groupby("target_date"):
        for model in models:
            rows.append(
                {
                    "target_month": pd.Timestamp(target_date).strftime("%Y-%m"),
                    "model": model,
                    "n": len(month),
                    **forecasting.evaluate(month, model),
                }
            )
    return pd.DataFrame(rows)


def cluster_bootstrap(frame: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    rng = np.random.default_rng(20260905)
    providers = frame.provider_code.drop_duplicates().to_numpy()
    distributions = {(model, metric): [] for model in models for metric in (
        "mae", "rmse", "r2", "spearman", "recall_at_20", "ndcg_at_20"
    )}
    groups = {provider: group for provider, group in frame.groupby("provider_code")}
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(providers, size=len(providers), replace=True)
        pieces = []
        for occurrence, provider in enumerate(sampled):
            piece = groups[provider].copy()
            piece.index = [f"{occurrence}:{idx}" for idx in piece.index]
            pieces.append(piece)
        replicate = pd.concat(pieces)
        for model in models:
            result = forecasting.evaluate(replicate, model)
            for metric in ("mae", "rmse", "r2", "spearman", "recall_at_20", "ndcg_at_20"):
                distributions[(model, metric)].append(result.get(metric, np.nan))
    rows = []
    for (model, metric), values in distributions.items():
        clean = np.asarray(values, dtype=float)
        clean = clean[np.isfinite(clean)]
        rows.append(
            {
                "model": model,
                "metric": metric,
                "estimate": forecasting.evaluate(frame, model).get(metric, np.nan),
                "ci_lower": float(np.quantile(clean, 0.025)),
                "ci_upper": float(np.quantile(clean, 0.975)),
                "bootstrap_unit": "provider",
                "replicates": BOOTSTRAP_REPLICATES,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    frame = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    available_models = model_columns(frame)
    output = OUTPUTS / "metrics"
    output.mkdir(parents=True, exist_ok=True)
    monthly_metrics(frame, available_models).to_csv(output / "monthly_test_metrics.csv", index=False)
    selected = json.loads((output / "selected_model.json").read_text(encoding="utf-8"))[
        "selected_model"
    ]
    intervals = cluster_bootstrap(frame, ["Persistence", selected])
    intervals.to_csv(output / "bootstrap_confidence_intervals.csv", index=False)
    summary = intervals[intervals.model.isin(["Persistence", selected])]
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
