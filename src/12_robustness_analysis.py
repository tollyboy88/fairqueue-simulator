"""Specialty and training-window robustness checks for the selected model."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as forecasting  # noqa: E402
from utils import OUTPUTS, PROCESSED  # noqa: E402


def main() -> None:
    metrics_dir = OUTPUTS / "metrics"
    selected_name = json.loads(
        (metrics_dir / "selected_model.json").read_text(encoding="utf-8")
    )["selected_model"]
    predictions = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    specialty_rows = []
    for specialty, group in predictions.groupby("treatment_function_name"):
        if len(group) < 100:
            continue
        specialty_rows.append(
            {
                "specialty": specialty,
                "n": len(group),
                **forecasting.point_metrics(
                    group[forecasting.TARGET], group[selected_name]
                ),
            }
        )
    pd.DataFrame(specialty_rows).sort_values("mae").to_csv(
        metrics_dir / "specialty_robustness.csv", index=False
    )

    data = pd.read_parquet(PROCESSED / "forecast_dataset.parquet")
    data = data[data.breach_52w_roll6.notna()].copy()
    test = data[data.split == "test"].copy()
    specs = {spec.name: spec for spec in forecasting.model_specs()}
    rows = []
    for label, start in (
        ("Primary training window", pd.Timestamp("2022-04-01")),
        ("Post-April-2023 training sensitivity", pd.Timestamp("2023-04-01")),
    ):
        development = data[
            data.split.isin(["train", "validation"]) & data.feature_date.ge(start)
        ]
        features = forecasting.FULL_FEATURES
        columns = forecasting.predictor_columns(features)
        model = forecasting.build_pipeline(specs[selected_name], features)
        model.fit(development[columns], development[forecasting.TARGET])
        test["robustness_prediction"] = model.predict(test[columns]).clip(0, 1)
        rows.append(
            {
                "analysis": label,
                "training_start": start.date().isoformat(),
                "n_development": len(development),
                **forecasting.evaluate(test, "robustness_prediction"),
            }
        )
    pd.DataFrame(rows).to_csv(metrics_dir / "training_window_robustness.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
