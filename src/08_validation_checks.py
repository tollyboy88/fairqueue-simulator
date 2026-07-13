"""
08_validation_checks.py
-----------------------
Run the blueprint's data / score / logic validation gates and write a report.
Output: outputs/metrics/validation_report.txt
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, OUTPUTS  # noqa


def main():
    rtt = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")
    scr = pd.read_parquet(PROCESSED / "priority_scores.parquet")
    lines, ok = [], True

    def check(name, condition):
        nonlocal ok
        ok = ok and bool(condition)
        lines.append(f"[{'PASS' if condition else 'FAIL'}] {name}")

    counts = ["incomplete_total", "breach_18w_count", "breach_52w_count",
              "dta_total", "new_rtt_total", "admitted_total", "non_admitted_total"]
    check("no negative counts", int((rtt[counts] < 0).sum().sum()) == 0)
    check("breach_18w <= incomplete", int((rtt.breach_18w_count > rtt.incomplete_total).sum()) == 0)
    check("breach_52w <= breach_18w", int((rtt.breach_52w_count > rtt.breach_18w_count).sum()) == 0)
    check("no duplicate provider-specialty-month",
          int(rtt.duplicated(["month", "provider_code", "treatment_function_code"]).sum()) == 0)
    check("valid months (12)", rtt.month.nunique() == 12)

    nn = [c for c in scr.columns if c.endswith("_n")]
    check("normalised scores within 0..1",
          bool(((scr[nn] >= -1e-9) & (scr[nn] <= 1 + 1e-9)).all().all()))
    check("final score within 0..100",
          bool(scr.priority_score_100.between(0, 100).all()))
    band_ok = (
        scr.loc[scr.priority_score_100 >= 80, "priority_level"].eq("Critical").all() and
        scr.loc[scr.priority_score_100.between(60, 79.999), "priority_level"].eq("High").all() and
        scr.loc[scr.priority_score_100 < 40, "priority_level"].eq("Lower").all())
    check("priority bands match score ranges", band_ok)

    # logic gates: correlations should have the expected sign
    check("higher 52w breach -> higher waiting score (corr>0)",
          scr.breach_52w_rate_n.corr(scr.waiting_pressure_score) > 0)
    check("higher missing-demographic -> higher fairness score (corr>0)",
          scr.missing_demographic_score_n.corr(scr.fairness_risk_score) > 0)

    header = ("FairQueue Simulator — validation report\n"
              f"rows(rtt)={len(rtt):,}  rows(scores)={len(scr):,}  "
              f"providers={rtt.provider_code.nunique()}  specialties={rtt.treatment_function_code.nunique()}\n"
              + "-" * 60 + "\n")
    report = header + "\n".join(lines) + f"\n\nOVERALL: {'ALL PASS' if ok else 'FAILURES PRESENT'}\n"
    (OUTPUTS / "metrics").mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "metrics" / "validation_report.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
