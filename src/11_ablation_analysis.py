"""Test whether operational context improves forecasts beyond RTT history."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as forecasting  # noqa: E402
from utils import OUTPUTS, PROCESSED  # noqa: E402

FEATURE_SETS = {
    "RTT history": forecasting.RTT_FEATURES,
    "RTT plus diagnostics": forecasting.DIAGNOSTIC_FEATURES,
    "RTT plus full operational context": forecasting.FULL_FEATURES,
}


def main() -> None:
    data = pd.read_parquet(PROCESSED / "forecast_dataset.parquet")
    data = data[data.breach_52w_roll6.notna()].copy()
    development = data[data.split.isin(["train", "validation"])]
    test = data[data.split == "test"].copy()
    selected_name = json.loads(
        (OUTPUTS / "metrics" / "selected_model.json").read_text(encoding="utf-8")
    )["selected_model"]
    specs = {spec.name: spec for spec in forecasting.model_specs()}
    if selected_name not in specs:
        raise RuntimeError(f"Selected estimator {selected_name!r} is unavailable")

    rows = []
    for label, features in FEATURE_SETS.items():
        columns = forecasting.predictor_columns(features)
        model = forecasting.build_pipeline(specs[selected_name], features)
        model.fit(development[columns], development[forecasting.TARGET])
        prediction = f"prediction_{len(rows)}"
        test[prediction] = model.predict(test[columns]).clip(0, 1)
        rows.append(
            {
                "feature_set": label,
                "model": selected_name,
                "feature_count": len(features) + len(forecasting.CATEGORICAL),
                **forecasting.evaluate(test, prediction),
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUTS / "metrics" / "ablation_results.csv", index=False)
    print(result.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
