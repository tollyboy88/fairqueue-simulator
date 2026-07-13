"""
05_build_features.py
--------------------
Join RTT + WLMDS fairness + operational pressure into the modelling dataset and
engineer every scoring component. Raw component -> winsorise(1/99) -> min-max 0..1
(suffix _n). Missing normalised components are filled with the column median
(neutral) so absent data neither inflates nor deflates pressure.

Output: data/processed/modelling_dataset.parquet
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, winsorise, minmax, safe_div  # noqa


def main():
    rtt = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")
    fair = pd.read_parquet(PROCESSED / "wlmds_fairness.parquet")
    op = pd.read_parquet(PROCESSED / "operational_pressure.parquet")

    df = rtt.merge(fair.drop(columns=["provider_name"], errors="ignore"),
                   on="provider_code", how="left")
    df = df.merge(op, on=["provider_code", "month"], how="left")

    # ---------- waiting-pressure raw components ----------
    df["breach_18w_rate"] = safe_div(df.breach_18w_count, df.incomplete_total)
    df["breach_52w_rate"] = safe_div(df.breach_52w_count, df.incomplete_total)
    df["dta_pressure"] = safe_div(df.dta_total, df.incomplete_total)
    df["demand_pressure"] = safe_div(df.new_rtt_total, df.incomplete_total)
    df["throughput_rate"] = safe_div(df.admitted_total + df.non_admitted_total, df.incomplete_total)
    df = df.sort_values(["provider_code", "treatment_function_code", "month"])
    df["backlog_growth_rate"] = (df.groupby(["provider_code", "treatment_function_code"])
                                 ["incomplete_total"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0))

    # ---------- operational composite raw components ----------
    df["ae_pressure_score"] = (0.40 * df.ae_4hr_breach_rate.fillna(df.ae_4hr_breach_rate.median())
                               + 0.30 * df.emergency_admission_rate.fillna(df.emergency_admission_rate.median())
                               + 0.30 * df.ae_dta_delay_rate.fillna(df.ae_dta_delay_rate.median()))
    df["diagnostic_bottleneck"] = df.diagnostic_over_6w_rate
    df["bed_pressure"] = df.bed_occupancy_rate
    df["theatre_pressure"] = 1 - df.theatre_daycase_share          # proxy: less day-case capacity = more pressure
    # cancellation: no elective-ops denominator -> normalise counts (blueprint fallback)
    canc_n = minmax(winsorise(df.cancelled_operations.fillna(0)))
    breach_n = minmax(winsorise(df.cancel_28day_breaches.fillna(0)))
    df["cancellation_pressure"] = 0.60 * canc_n + 0.40 * breach_n

    # ---------- normalise everything to 0..1 ----------
    to_norm = [
        "breach_18w_rate", "breach_52w_rate", "dta_pressure", "demand_pressure",
        "backlog_growth_rate", "throughput_rate",
        "fairness_deprivation_score", "fairness_ethnicity_score",
        "fairness_age_score", "fairness_sex_score", "missing_demographic_score",
        "diagnostic_bottleneck", "bed_pressure", "ae_pressure_score",
        "cancellation_pressure", "theatre_pressure",
    ]
    for c in to_norm:
        if c not in df.columns:
            df[c] = np.nan
        df[c + "_n"] = minmax(winsorise(df[c].astype(float)))
    df["inverse_throughput_n"] = 1 - df["throughput_rate_n"]

    # fill missing normalised components with neutral column median
    for c in [c + "_n" for c in to_norm] + ["inverse_throughput_n"]:
        med = df[c].median()
        df[c] = df[c].fillna(med if pd.notna(med) else 0.0)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "modelling_dataset.parquet"
    df.to_parquet(out, index=False)
    print(f"modelling_dataset.parquet: {df.shape[0]:,} rows x {df.shape[1]} cols -> {out}")
    print("normalised components range check (should be 0..1):")
    nn = [c for c in df.columns if c.endswith('_n')]
    print(df[nn].agg(['min', 'max']).T.round(3).to_string())


if __name__ == "__main__":
    main()
