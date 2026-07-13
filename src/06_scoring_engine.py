"""
06_scoring_engine.py
--------------------
Apply the three transparent sub-scores and the final weighted priority score
(blueprint sections 8-13) to the modelling dataset.

    waiting_pressure_score = 0.30 b18 + 0.25 b52 + 0.15 dta + 0.15 backlog
                           + 0.10 demand + 0.05 inverse_throughput
    fairness_risk_score    = 0.30 deprivation + 0.25 ethnicity + 0.20 age
                           + 0.15 sex + 0.10 missing_demographic
    operational_pressure   = 0.25 diagnostic + 0.25 bed + 0.20 ae
                           + 0.15 cancellation + 0.15 theatre
    final_priority_score   = 0.50 waiting + 0.30 fairness + 0.20 operational
    priority_score_100     = final x 100   ->   Lower/Moderate/High/Critical

Output: data/processed/priority_scores.parquet
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, priority_level  # noqa

W_FINAL = {"waiting": 0.50, "fairness": 0.30, "operational": 0.20}


def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["waiting_pressure_score"] = (
        0.30 * df.breach_18w_rate_n + 0.25 * df.breach_52w_rate_n
        + 0.15 * df.dta_pressure_n + 0.15 * df.backlog_growth_rate_n
        + 0.10 * df.demand_pressure_n + 0.05 * df.inverse_throughput_n)
    df["fairness_risk_score"] = (
        0.30 * df.fairness_deprivation_score_n + 0.25 * df.fairness_ethnicity_score_n
        + 0.20 * df.fairness_age_score_n + 0.15 * df.fairness_sex_score_n
        + 0.10 * df.missing_demographic_score_n)
    df["operational_pressure_score"] = (
        0.25 * df.diagnostic_bottleneck_n + 0.25 * df.bed_pressure_n
        + 0.20 * df.ae_pressure_score_n + 0.15 * df.cancellation_pressure_n
        + 0.15 * df.theatre_pressure_n)
    df["final_priority_score"] = (
        W_FINAL["waiting"] * df.waiting_pressure_score
        + W_FINAL["fairness"] * df.fairness_risk_score
        + W_FINAL["operational"] * df.operational_pressure_score)
    df["priority_score_100"] = (df.final_priority_score * 100).round(2)
    df["priority_level"] = df.priority_score_100.apply(priority_level)
    return df


def main():
    df = pd.read_parquet(PROCESSED / "modelling_dataset.parquet")
    scored = add_scores(df)

    keep = ["month", "quarter", "financial_year", "region_code", "provider_code",
            "provider_name", "treatment_function_code", "treatment_function_name",
            "incomplete_total", "breach_18w_count", "breach_52w_count", "dta_total",
            "new_rtt_total", "admitted_total", "non_admitted_total",
            "waiting_pressure_score", "fairness_risk_score", "operational_pressure_score",
            "final_priority_score", "priority_score_100", "priority_level"]
    keep += [c for c in scored.columns if c.endswith("_n")]
    out = scored[keep].copy()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / "priority_scores.parquet", index=False)

    print(f"priority_scores.parquet: {len(out):,} rows")
    print("\nscore ranges:")
    print(out[["waiting_pressure_score", "fairness_risk_score",
               "operational_pressure_score", "priority_score_100"]].describe().round(2).loc[
        ["min", "mean", "max"]].T.to_string())
    print("\npriority level counts:")
    print(out.priority_level.value_counts().to_string())
    latest = out.month.max()
    print(f"\nTop 10 critical areas ({latest}):")
    t = out[out.month == latest].nlargest(10, "priority_score_100")
    print(t[["provider_name", "treatment_function_name", "waiting_pressure_score",
             "fairness_risk_score", "operational_pressure_score",
             "priority_score_100", "priority_level"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
