"""Month-level evaluation and provider-cluster bootstrap intervals."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as forecasting  # noqa: E402
from utils import OUTPUTS, PROCESSED  # noqa: E402

BOOTSTRAP_REPLICATES = 1_000
BOOTSTRAP_METRICS = (
    "mae", "rmse", "r2", "spearman", "recall_at_20", "ndcg_at_20"
)


def model_columns(frame: pd.DataFrame) -> list[str]:
    excluded = set(forecasting.predictor_columns(forecasting.FULL_FEATURES)) | {
        "feature_date",
        "forecast_decision_date",
        "target_date",
        "target_available_date",
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


def cluster_bootstrap(
    frame: pd.DataFrame,
    models: list[str],
    learned_model: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(20260905)
    providers, provider_index = np.unique(
        frame.provider_code.to_numpy(), return_inverse=True
    )
    distributions = {
        (model, metric): [] for model in models for metric in BOOTSTRAP_METRICS
    }
    row_numbers = np.arange(len(frame))
    true = frame[forecasting.TARGET].to_numpy(dtype=float)
    predictions = {
        model: frame[model].to_numpy(dtype=float) for model in models
    }
    month_rows = [
        group.index.to_numpy()
        for _, group in frame.reset_index(drop=True).groupby("target_date")
    ]

    def evaluate_resample(model: str, weights: np.ndarray) -> dict[str, float]:
        replicated_rows = np.repeat(row_numbers, weights)
        result = forecasting.point_metrics(
            true[replicated_rows], predictions[model][replicated_rows]
        )
        recalls, ndcgs = [], []
        for rows in month_rows:
            expanded = np.repeat(rows, weights[rows])
            if len(expanded) < 2:
                continue
            observed = true[expanded]
            predicted = predictions[model][expanded]
            k = min(20, len(expanded))
            actual_order = np.argsort(-observed, kind="stable")[:k]
            predicted_order = np.argsort(-predicted, kind="stable")[:k]
            recalls.append(
                len(set(actual_order.tolist()) & set(predicted_order.tolist())) / k
            )
            ndcgs.append(
                float(ndcg_score(observed.reshape(1, -1), predicted.reshape(1, -1), k=k))
            )
        result["recall_at_20"] = float(np.mean(recalls))
        result["ndcg_at_20"] = float(np.mean(ndcgs))
        return result

    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = rng.integers(0, len(providers), size=len(providers))
        provider_weights = np.bincount(sampled, minlength=len(providers))
        row_weights = provider_weights[provider_index]
        for model in models:
            result = evaluate_resample(model, row_weights)
            for metric in BOOTSTRAP_METRICS:
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
    paired_rows = []
    point_results = {model: forecasting.evaluate(frame, model) for model in models}
    for metric in ("mae", "rmse", "ndcg_at_20"):
        learned = np.asarray(distributions[(learned_model, metric)], dtype=float)
        persistence = np.asarray(distributions[("Persistence", metric)], dtype=float)
        differences = learned - persistence
        clean = differences[np.isfinite(differences)]
        paired_rows.append(
            {
                "comparison": f"{learned_model} minus Persistence",
                "metric": metric,
                "estimate": point_results[learned_model][metric]
                - point_results["Persistence"][metric],
                "ci_lower": float(np.quantile(clean, 0.025)),
                "ci_upper": float(np.quantile(clean, 0.975)),
                "difference_definition": "selected learned model minus Persistence",
                "bootstrap_unit": "provider",
                "replicates": BOOTSTRAP_REPLICATES,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(paired_rows)


def main() -> None:
    frame = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    available_models = model_columns(frame)
    output = OUTPUTS / "metrics"
    output.mkdir(parents=True, exist_ok=True)
    monthly_metrics(frame, available_models).to_csv(output / "monthly_test_metrics.csv", index=False)
    specification = json.loads(
        (output / "selected_model.json").read_text(encoding="utf-8")
    )
    selected = specification["primary_forecaster"]
    learned = specification["selected_learned_model"]
    intervals, paired = cluster_bootstrap(frame, [selected, learned], learned)
    intervals.to_csv(output / "bootstrap_confidence_intervals.csv", index=False)
    paired.to_csv(output / "paired_bootstrap_differences.csv", index=False)
    summary = intervals[intervals.model.isin([selected, learned])]
    print(summary.round(4).to_string(index=False))
    print("\nPaired differences (learned minus Persistence)")
    print(paired.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
