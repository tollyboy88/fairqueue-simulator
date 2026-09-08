"""Build dated, leakage-safe forecasting features.

All rolling quantities use only the current or earlier RTT month. Operational
sources have already been shifted to their conservative availability month.
No imputation, clipping or scaling is fitted in this step.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, safe_div  # noqa: E402

KEYS = ["provider_code", "treatment_function_code"]


def assert_sources_available(data: pd.DataFrame) -> None:
    """Reject predictors whose source was unpublished at the forecast decision date."""
    if data["forecast_decision_date"].isna().any():
        raise AssertionError("RTT forecast decision date is missing")
    availability_checks = {
        "diagnostic_over_6w_rate": "diagnostic_available_date",
        "bed_occupancy_rate": "bed_available_date",
        "cancelled_operations": "cancellation_available_date",
    }
    for value_column, available_column in availability_checks.items():
        populated = data[value_column].notna()
        if data.loc[populated, available_column].isna().any():
            raise AssertionError(f"{value_column} lacks a publication date")
        if (
            pd.to_datetime(data.loc[populated, available_column])
            > data.loc[populated, "forecast_decision_date"]
        ).any():
            raise AssertionError(f"{value_column} is unavailable at forecast time")


def build_features(rtt: pd.DataFrame, operational: pd.DataFrame) -> pd.DataFrame:
    data = rtt.copy()
    data["month"] = data["month"].astype(str)
    data = data.merge(operational, on=["provider_code", "month"], how="left")
    data["feature_date"] = pd.PeriodIndex(data["month"], freq="M").to_timestamp("M")
    data["forecast_decision_date"] = pd.to_datetime(data["rtt_available_date"])
    assert_sources_available(data)
    data = data.sort_values([*KEYS, "feature_date"]).reset_index(drop=True)

    data["breach_18w_rate"] = safe_div(data.breach_18w_count, data.incomplete_total)
    data["breach_52w_rate"] = safe_div(data.breach_52w_count, data.incomplete_total)
    data["dta_rate"] = safe_div(data.dta_total, data.incomplete_total)
    data["demand_rate"] = safe_div(data.new_rtt_total, data.incomplete_total)
    data["throughput_rate"] = safe_div(
        data.admitted_total + data.non_admitted_total, data.incomplete_total
    )
    data["demand_throughput_ratio"] = safe_div(
        data.new_rtt_total, data.admitted_total + data.non_admitted_total
    )

    grouped = data.groupby(KEYS, sort=False)
    for column in ("incomplete_total", "breach_18w_rate", "breach_52w_rate", "throughput_rate"):
        data[f"{column}_lag1"] = grouped[column].shift(1)
        data[f"{column}_lag3"] = grouped[column].shift(3)
    data["breach_52w_rate_lag2"] = grouped["breach_52w_rate"].shift(2)
    data["backlog_growth_rate"] = (
        data.incomplete_total / data.incomplete_total_lag1.replace(0, np.nan) - 1
    )
    data["breach_52w_mom_change"] = data.breach_52w_rate - data.breach_52w_rate_lag1
    data["breach_52w_trend3"] = (
        data.breach_52w_rate - data.breach_52w_rate_lag3
    ) / 3
    data["breach_52w_acceleration"] = (
        data.breach_52w_rate
        - 2 * data.breach_52w_rate_lag1
        + data.breach_52w_rate_lag2
    )
    for window in (3, 6):
        data[f"breach_52w_roll{window}"] = grouped["breach_52w_rate"].transform(
            lambda series: series.rolling(window, min_periods=window).mean()
        )
        data[f"incomplete_roll{window}"] = grouped["incomplete_total"].transform(
            lambda series: series.rolling(window, min_periods=window).mean()
        )

    month_number = data.feature_date.dt.month
    data["month_sin"] = np.sin(2 * np.pi * month_number / 12)
    data["month_cos"] = np.cos(2 * np.pi * month_number / 12)
    data["log_incomplete_total"] = np.log1p(data.incomplete_total.clip(lower=0))
    data["log_cancelled_operations"] = np.log1p(
        pd.to_numeric(data.get("cancelled_operations"), errors="coerce").clip(lower=0)
    )
    data["cancel_28day_breach_rate"] = safe_div(
        pd.to_numeric(data.get("cancel_28day_breaches"), errors="coerce"),
        pd.to_numeric(data.get("cancelled_operations"), errors="coerce"),
    )
    return data


def main() -> None:
    rtt = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")
    operational = pd.read_parquet(PROCESSED / "operational_pressure.parquet")
    result = build_features(rtt, operational)
    output = PROCESSED / "longitudinal_features.parquet"
    result.to_parquet(output, index=False)
    print(
        f"Wrote {len(result):,} dated feature rows; "
        f"{result.feature_date.min().date()} to {result.feature_date.max().date()}"
    )


if __name__ == "__main__":
    main()
