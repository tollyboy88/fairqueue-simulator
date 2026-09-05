"""Attach independently observed t+1 and t+3 RTT outcomes."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, safe_div  # noqa: E402

KEYS = ["provider_code", "treatment_function_code"]
TRAIN_END = pd.Timestamp("2024-12-31")
VALIDATION_END = pd.Timestamp("2025-06-30")
TEST_END = pd.Timestamp("2026-03-31")


def assign_split(feature_date: pd.Series) -> pd.Series:
    dates = pd.to_datetime(feature_date)
    return pd.Series(
        np.select(
            [
                dates <= TRAIN_END,
                dates <= VALIDATION_END,
                dates <= TEST_END,
            ],
            ["train", "validation", "test"],
            default="outside",
        ),
        index=feature_date.index,
    )


def build_targets(features: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    base = features.copy()
    base["target_period"] = pd.PeriodIndex(base["month"], freq="M") + horizon
    outcomes = base[
        [*KEYS, "month", "incomplete_total", "breach_52w_count", "breach_18w_count"]
    ].copy()
    outcomes["target_period"] = pd.PeriodIndex(outcomes["month"], freq="M")
    outcomes["target_breach_52w_rate"] = safe_div(
        outcomes.breach_52w_count, outcomes.incomplete_total
    )
    outcomes["target_breach_18w_rate"] = safe_div(
        outcomes.breach_18w_count, outcomes.incomplete_total
    )
    outcomes = outcomes.rename(columns={"incomplete_total": "target_incomplete_total"})
    outcomes = outcomes[
        [
            *KEYS,
            "target_period",
            "target_incomplete_total",
            "target_breach_52w_rate",
            "target_breach_18w_rate",
        ]
    ]
    result = base.merge(outcomes, on=[*KEYS, "target_period"], how="inner")
    result["target_date"] = result.target_period.dt.to_timestamp("M")
    result["target_change_52w"] = (
        result.target_breach_52w_rate - result.breach_52w_rate
    )
    result["horizon_months"] = horizon
    result["split"] = assign_split(result.feature_date)
    result = result[
        (result.incomplete_total >= 100)
        & (result.target_incomplete_total >= 100)
        & result.split.ne("outside")
    ].copy()
    return result.sort_values(["feature_date", *KEYS]).reset_index(drop=True)


def main() -> None:
    features = pd.read_parquet(PROCESSED / "longitudinal_features.parquet")
    result = build_targets(features, horizon=3)
    output = PROCESSED / "forecast_dataset.parquet"
    result.to_parquet(output, index=False)
    print(f"Wrote {len(result):,} forecast rows to {output}")
    print(result.groupby("split").agg(rows=("month", "size"), months=("month", "nunique")).to_string())
    assert (result.feature_date < result.target_date).all()


if __name__ == "__main__":
    main()
