"""
09_make_charts.py
-----------------
Static charts for the paper / outputs. Saves PNGs to outputs/charts/.
"""
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, OUTPUTS  # noqa

CH = OUTPUTS / "charts"
CH.mkdir(parents=True, exist_ok=True)


def main():
    rtt = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")
    scr = pd.read_parquet(PROCESSED / "priority_scores.parquet")
    ov = pd.read_csv(OUTPUTS / "metrics" / "strategy_metrics.csv")
    latest = scr.month.max()

    # 1) national waiting-list trend
    g = rtt.groupby("month").agg(incomplete=("incomplete_total", "sum"),
                                 b18=("breach_18w_count", "sum"),
                                 b52=("breach_52w_count", "sum"))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(g.index, g.incomplete / 1e6, marker="o", label="Incomplete pathways (m)")
    ax.plot(g.index, g.b18 / 1e6, marker="s", label="Waiting >18 weeks (m)")
    ax.plot(g.index, g.b52 / 1e6, marker="^", label="Waiting >52 weeks (m)")
    ax.set_title("National RTT waiting-list trend, 2025/26")
    ax.set_ylabel("Patients (millions)"); ax.tick_params(axis="x", rotation=45)
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
    fig.savefig(CH / "national_waiting_trend.png", dpi=130); plt.close(fig)

    # 2) top-10 priority provider-specialty areas (latest month)
    t = scr[scr.month == latest].nlargest(10, "priority_score_100").iloc[::-1]
    lbl = (t.provider_name.str.title().str.replace(" Nhs", " NHS") + " — "
           + t.treatment_function_name.str.replace(" Service", ""))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(lbl, t.priority_score_100, color="#b5179e")
    ax.set_title(f"Top 10 priority areas — full fairness-aware model ({latest})")
    ax.set_xlabel("Priority score (0–100)"); ax.grid(axis="x", alpha=.3); fig.tight_layout()
    fig.savefig(CH / "top10_priority_areas.png", dpi=130); plt.close(fig)

    # 3) strategy top-20 overlap with waiting-time-only
    o = ov[ov.month == latest].sort_values("top20_overlap_with_waiting_only")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(o.strategy.str.replace("_", " "), o.top20_overlap_with_waiting_only, color="#3a0ca3")
    ax.set_xlim(0, 1); ax.set_title(f"Top-20 overlap with waiting-time-only ({latest})")
    ax.set_xlabel("Share of shared areas"); ax.grid(axis="x", alpha=.3); fig.tight_layout()
    fig.savefig(CH / "strategy_top20_overlap.png", dpi=130); plt.close(fig)

    # 4) rank shift under fairness-aware vs waiting-only
    sc = pd.read_parquet(PROCESSED / "strategy_comparison.parquet")
    sh = sc[sc.month == latest]["shift_full_fairness_aware"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(sh, bins=40, color="#4361ee")
    ax.axvline(0, color="k", lw=1)
    ax.set_title(f"Rank shift: fairness-aware vs waiting-time-only ({latest})")
    ax.set_xlabel("Rank improvement (positive = rises with fairness)"); ax.set_ylabel("Areas")
    ax.grid(alpha=.3); fig.tight_layout()
    fig.savefig(CH / "rank_shift_fairness.png", dpi=130); plt.close(fig)

    print("Saved charts:", *[p.name for p in sorted(CH.glob("*.png"))])


if __name__ == "__main__":
    main()
