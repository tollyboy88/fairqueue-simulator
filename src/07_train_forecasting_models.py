"""Select forecasting algorithms on validation months and freeze them for test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as forecasting  # noqa: E402
from utils import OUTPUTS, PROCESSED  # noqa: E402


def main() -> None:
    data = pd.read_parquet(PROCESSED / "forecast_dataset.parquet")
    data = data[data.breach_52w_roll6.notna()].copy()
    train = data[data.split == "train"]
    validation = data[data.split == "validation"]
    test = data[data.split == "test"]
    development = data[data.split.isin(["train", "validation"])]
    if min(len(train), len(validation), len(test)) == 0:
        raise RuntimeError("Chronological split produced an empty partition")

    metrics_dir = OUTPUTS / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    features = forecasting.FULL_FEATURES
    columns = forecasting.predictor_columns(features)

    validation_predictions = forecasting.baseline_predictions(validation)
    validation_rows = []
    for baseline in ("Persistence", "Three-month mean"):
        validation_rows.append(
            {
                "model": baseline,
                "partition": "validation",
                **forecasting.evaluate(validation_predictions, baseline),
            }
        )

    fitted_validation = {}
    for spec in forecasting.model_specs():
        print(f"validation fit: {spec.name}")
        pipeline = forecasting.build_pipeline(spec, features)
        pipeline.fit(train[columns], train[forecasting.TARGET])
        validation_predictions[spec.name] = pipeline.predict(validation[columns]).clip(0, 1)
        fitted_validation[spec.name] = pipeline
        validation_rows.append(
            {
                "model": spec.name,
                "partition": "validation",
                **forecasting.evaluate(validation_predictions, spec.name),
            }
        )
    validation_metrics = pd.DataFrame(validation_rows).sort_values("mae")
    validation_metrics.to_csv(metrics_dir / "validation_model_metrics.csv", index=False)
    candidate_names = set(fitted_validation)
    selected_name = validation_metrics[
        validation_metrics.model.isin(candidate_names)
    ].iloc[0].model
    print(f"Selected on validation MAE: {selected_name}")

    identifiers = [
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
    ]
    selected_columns = list(dict.fromkeys([*identifiers, *columns]))
    test_predictions = forecasting.baseline_predictions(test[selected_columns].copy())
    test_rows = []
    for baseline in ("Persistence", "Three-month mean"):
        test_rows.append(
            {
                "model": baseline,
                "partition": "test",
                **forecasting.evaluate(test_predictions, baseline),
            }
        )

    final_models = {}
    for spec in forecasting.model_specs():
        print(f"final fit: {spec.name}")
        pipeline = forecasting.build_pipeline(spec, features)
        pipeline.fit(development[columns], development[forecasting.TARGET])
        test_predictions[spec.name] = pipeline.predict(test[columns]).clip(0, 1)
        final_models[spec.name] = pipeline
        test_rows.append(
            {
                "model": spec.name,
                "partition": "test",
                **forecasting.evaluate(test_predictions, spec.name),
            }
        )

    test_metrics = pd.DataFrame(test_rows).sort_values("mae")
    test_metrics.to_csv(metrics_dir / "test_model_metrics.csv", index=False)
    test_predictions.to_parquet(PROCESSED / "test_predictions.parquet", index=False)
    forecasting.save_bundle(final_models[selected_name], features, selected_name)
    forecasting.feature_importance(
        final_models[selected_name], test, features
    ).to_csv(metrics_dir / "permutation_feature_importance.csv", index=False)

    specification = {
        "selection_metric": "validation MAE",
        "selected_model": selected_name,
        "target": "observed provider-specialty 52-week breach rate at t+3",
        "features": features,
        "categorical_features": forecasting.CATEGORICAL,
        "train_end": "2024-12-31",
        "validation_end": "2025-06-30",
        "test_feature_period": "2025-07 through 2026-03",
        "test_target_period": "2025-10 through 2026-06",
        "test_used_for_selection": False,
        "n_train": int(len(train)),
        "n_validation": int(len(validation)),
        "n_test": int(len(test)),
    }
    (metrics_dir / "selected_model.json").write_text(
        json.dumps(specification, indent=2), encoding="utf-8"
    )
    print(test_metrics.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
