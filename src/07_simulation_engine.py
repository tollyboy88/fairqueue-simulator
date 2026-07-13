"""
07_simulation_engine.py
-----------------------
Compute the five prioritisation strategies, rank provider-specialty areas within
each month, and produce the comparison metrics that drive the paper.

Strategies (blueprint section 14):
    S1 waiting_time_only   = 0.60 b18 + 0.40 b52
    S2 operational         = 0.50 waiting + 0.50 operational
    S3 cancellation_aware  = 0.45 waiting + 0.35 cancellation + 0.20 bed_theatre
    S4 deprivation_weighted= 0.60 waiting + 0.40 deprivation
    S5 full_fairness_aware = 0.50 waiting + 0.30 fairness + 0.20 operational (proposed)

Outputs:
    data/processed/strategy_comparison.parquet
    outputs/tables/top_20_priority_areas.csv
    outputs/metrics/strategy_metrics.csv
    outputs/metrics/fairness_lift_results.csv
    outputs/metrics/sensitivity_analysis.csv
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, OUTPUTS  # noqa

STRATS = {
    "waiting_time_only": lambda d: 0.60 * d.breach_18w_rate_n + 0.40 * d.breach_52w_rate_n,
    "operational": lambda d: 0.50 * d.waiting_pressure_score + 0.50 * d.operational_pressure_score,
    "cancellation_aware": lambda d: (0.45 * d.waiting_pressure_score
                                     + 0.35 * d.cancellation_pressure_n
                                     + 0.20 * (d.bed_pressure_n + d.theatre_pressure_n) / 2),
    "deprivation_weighted": lambda d: 0.60 * d.waiting_pressure_score + 0.40 * d.fairness_deprivation_score_n,
    "full_fairness_aware": lambda d: d.final_priority_score,
}
KEYS = ["month", "provider_code", "treatment_function_code"]
ID = ["month", "provider_name", "treatment_function_name"]


def build(df):
    out = df[KEYS + ID[1:] + ["waiting_pressure_score", "fairness_risk_score",
                              "operational_pressure_score", "final_priority_score",
                              "priority_score_100", "priority_level"]].copy()
    for s, fn in STRATS.items():
        out[f"score_{s}"] = fn(df)
        out[f"rank_{s}"] = out.groupby("month")[f"score_{s}"].rank(ascending=False, method="min")
    # rank shift vs waiting-time-only (positive = rises under the strategy)
    for s in STRATS:
        if s == "waiting_time_only":
            continue
        out[f"shift_{s}"] = out["rank_waiting_time_only"] - out[f"rank_{s}"]
    return out


def topk_overlap(out, k=20):
    rows = []
    for month, g in out.groupby("month"):
        base = set(g.nsmallest(k, "rank_waiting_time_only")[KEYS[1:]].apply(tuple, axis=1))
        for s in STRATS:
            if s == "waiting_time_only":
                continue
            cur = set(g.nsmallest(k, f"rank_{s}")[KEYS[1:]].apply(tuple, axis=1))
            rows.append({"month": month, "strategy": s,
                         "top20_overlap_with_waiting_only": len(base & cur) / k})
    return pd.DataFrame(rows)


def lifts(df, k=20):
    """fairness / operational / cancellation lift on the latest month."""
    m = df.month.max()
    g = df[df.month == m]
    base = g.nsmallest(k, g["breach_18w_rate_n"].rank(ascending=False, method="min").name) \
        if False else g.assign(r=g.eval("0.60*breach_18w_rate_n+0.40*breach_52w_rate_n")) \
        .nlargest(k, "r")
    fa = g.nlargest(k, "final_priority_score")
    op = g.assign(r=0.5 * g.waiting_pressure_score + 0.5 * g.operational_pressure_score).nlargest(k, "r")
    ca = g.assign(r=0.45 * g.waiting_pressure_score + 0.35 * g.cancellation_pressure_n
                  + 0.20 * (g.bed_pressure_n + g.theatre_pressure_n) / 2).nlargest(k, "r")
    return pd.DataFrame([
        {"metric": "fairness_lift", "month": m,
         "value": fa.fairness_risk_score.mean() - base.fairness_risk_score.mean()},
        {"metric": "operational_lift", "month": m,
         "value": op.operational_pressure_score.mean() - base.operational_pressure_score.mean()},
        {"metric": "cancellation_impact", "month": m,
         "value": ca.cancellation_pressure_n.mean() - base.cancellation_pressure_n.mean()},
    ])


def sensitivity(df, k=20):
    """Stability of the top-20 (latest month) across weight scenarios."""
    m = df.month.max()
    g = df[df.month == m].copy()
    scenarios = {"main": (0.50, 0.30, 0.20), "A": (0.60, 0.25, 0.15),
                 "B": (0.40, 0.40, 0.20), "C": (0.45, 0.25, 0.30)}
    tops = {}
    for name, (w, f, o) in scenarios.items():
        g["s"] = w * g.waiting_pressure_score + f * g.fairness_risk_score + o * g.operational_pressure_score
        tops[name] = set(g.nlargest(k, "s")[KEYS[1:]].apply(tuple, axis=1))
    main = tops["main"]
    rows = [{"scenario": n, "weights_w_f_o": str(scenarios[n]),
             "overlap_with_main_top20": len(main & t) / k} for n, t in tops.items()]
    stable = set.intersection(*tops.values())
    rows.append({"scenario": "ALL", "weights_w_f_o": "intersection",
                 "overlap_with_main_top20": len(stable) / k})
    return pd.DataFrame(rows)


def main():
    df = pd.read_parquet(PROCESSED / "priority_scores.parquet")
    out = build(df)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / "strategy_comparison.parquet", index=False)

    (OUTPUTS / "tables").mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "metrics").mkdir(parents=True, exist_ok=True)

    m = df.month.max()
    top20 = (df[df.month == m].nlargest(20, "priority_score_100")
             [["provider_name", "treatment_function_name", "waiting_pressure_score",
               "fairness_risk_score", "operational_pressure_score",
               "priority_score_100", "priority_level"]].round(3))
    top20.to_csv(OUTPUTS / "tables" / "top_20_priority_areas.csv", index=False)

    ov = topk_overlap(out)
    ov.to_csv(OUTPUTS / "metrics" / "strategy_metrics.csv", index=False)
    lift = lifts(df); lift.to_csv(OUTPUTS / "metrics" / "fairness_lift_results.csv", index=False)
    sens = sensitivity(df); sens.to_csv(OUTPUTS / "metrics" / "sensitivity_analysis.csv", index=False)

    print(f"strategy_comparison.parquet: {len(out):,} rows")
    print(f"\nTop-20 overlap with waiting-time-only (latest month {m}):")
    print(ov[ov.month == m][["strategy", "top20_overlap_with_waiting_only"]].round(2).to_string(index=False))
    print("\nLifts (latest month):")
    print(lift.round(3).to_string(index=False))
    print("\nSensitivity (top-20 stability vs main weights):")
    print(sens.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
