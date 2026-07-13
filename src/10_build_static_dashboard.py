"""
10_build_static_dashboard.py
----------------------------
Render a single, self-contained HTML dashboard (no server needed) that mirrors
the Streamlit pages. Open outputs/FairQueue_Dashboard.html in any browser.
"""
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.io as pio

sys.path.append(str(Path(__file__).resolve().parent))
from utils import PROCESSED, INTERIM, OUTPUTS  # noqa

pio.templates.default = "plotly_white"
F = dict(full_html=False, include_plotlyjs=False, default_height="420px")


def fig_html(fig):
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig.to_html(**F)


def main():
    scr = pd.read_parquet(PROCESSED / "priority_scores.parquet")
    rtt = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")
    sc = pd.read_parquet(PROCESSED / "strategy_comparison.parquet")
    det = pd.read_parquet(INTERIM / "wlmds_cleaned" / "wlmds_fairness_detail.parquet")
    ov = pd.read_csv(OUTPUTS / "metrics" / "strategy_metrics.csv")
    lift = pd.read_csv(OUTPUTS / "metrics" / "fairness_lift_results.csv")
    sens = pd.read_csv(OUTPUTS / "metrics" / "sensitivity_analysis.csv")
    latest = scr.month.max()

    # ---- Overview
    g = rtt.groupby("month", as_index=False).agg(
        Incomplete=("incomplete_total", "sum"), Over18w=("breach_18w_count", "sum"),
        Over52w=("breach_52w_count", "sum"))
    f_trend = px.line(g, x="month", y=["Incomplete", "Over18w", "Over52w"], markers=True,
                      title="National RTT waiting-list trend, 2025/26",
                      labels={"value": "Patients", "month": "Month", "variable": ""})
    sp = (scr[scr.month == latest].groupby("treatment_function_name", as_index=False)
          .waiting_pressure_score.mean().nlargest(10, "waiting_pressure_score"))
    f_spec = px.bar(sp, x="waiting_pressure_score", y="treatment_function_name", orientation="h",
                    title=f"Top 10 pressured specialties ({latest})",
                    labels={"waiting_pressure_score": "Mean waiting pressure", "treatment_function_name": ""})
    pp = (scr[scr.month == latest].groupby("provider_name", as_index=False)
          .priority_score_100.mean().nlargest(10, "priority_score_100"))
    f_prov = px.bar(pp, x="priority_score_100", y="provider_name", orientation="h",
                    title=f"Top 10 pressured providers ({latest})",
                    labels={"priority_score_100": "Mean priority score", "provider_name": ""})
    lr = g[g.month == latest].iloc[0]
    kpis = [("Incomplete pathways", f"{lr.Incomplete/1e6:.2f} m"),
            ("% within 18 weeks", f"{100*(1-lr.Over18w/lr.Incomplete):.1f}%"),
            ("Waiting >52 weeks", f"{lr.Over52w/1e3:,.0f} k"),
            ("Provider-specialty areas", f"{scr[scr.month==latest].shape[0]:,}")]

    # ---- Ranking
    rank = (scr[scr.month == latest].nlargest(40, "priority_score_100")
            [["provider_name", "treatment_function_name", "waiting_pressure_score",
              "fairness_risk_score", "operational_pressure_score", "priority_score_100", "priority_level"]]
            .round(2))
    rank.columns = ["Provider", "Specialty", "Waiting", "Fairness", "Operational", "Priority", "Level"]
    rank.insert(0, "Rank", range(1, len(rank) + 1))

    # ---- Fairness
    pname = scr[["provider_code", "provider_name"]].drop_duplicates().set_index("provider_code").provider_name.to_dict()
    det = det.copy(); det["provider_name"] = det.provider_code.map(pname).fillna(det.provider_code)
    wal = det[(det.metric == "IMD") & (det.provider_name == "WALSALL HEALTHCARE NHS TRUST")].sort_values("fairness_gap")
    f_fair = px.bar(wal, x="fairness_gap", y="Category", orientation="h", color="fairness_gap",
                    color_continuous_scale="RdBu_r",
                    title="Deprivation (IMD) fairness gaps — Walsall Healthcare (1 = most deprived)",
                    labels={"fairness_gap": "Share of long waits − share of all waits", "Category": "IMD decile"})
    fr = (scr.groupby("provider_name", as_index=False).fairness_risk_score.mean()
          .nlargest(15, "fairness_risk_score"))
    f_frprov = px.bar(fr, x="fairness_risk_score", y="provider_name", orientation="h",
                      title="Top 15 providers by fairness-risk score",
                      labels={"fairness_risk_score": "Fairness-risk score", "provider_name": ""})

    # ---- Operational
    mod = pd.read_parquet(PROCESSED / "modelling_dataset.parquet")
    d = mod[mod.month == latest]
    comp = {"Diagnostic >6w": "diagnostic_bottleneck_n", "Bed occupancy": "bed_pressure_n",
            "A&E pressure": "ae_pressure_score_n", "Cancellation": "cancellation_pressure_n",
            "Theatre": "theatre_pressure_n"}
    means = pd.DataFrame({"Component": list(comp), "Mean": [d[v].mean() for v in comp.values()]})
    f_op = px.bar(means.sort_values("Mean"), x="Mean", y="Component", orientation="h",
                  title=f"Average operational pressure components ({latest})",
                  labels={"Mean": "Mean normalised pressure"})

    # ---- Simulation
    o = ov[ov.month == latest].copy()
    labmap = {"waiting_time_only": "Waiting-time only", "operational": "Operational",
              "cancellation_aware": "Cancellation-aware", "deprivation_weighted": "Deprivation-weighted",
              "full_fairness_aware": "Full fairness-aware"}
    o["strategy"] = o.strategy.map(labmap)
    f_ov = px.bar(o.sort_values("top20_overlap_with_waiting_only"),
                  x="top20_overlap_with_waiting_only", y="strategy", orientation="h", range_x=[0, 1],
                  title=f"Top-20 overlap with waiting-time-only ({latest})",
                  labels={"top20_overlap_with_waiting_only": "Shared share of top-20", "strategy": ""})
    movers = (sc[sc.month == latest].nlargest(15, "shift_full_fairness_aware")
              [["provider_name", "treatment_function_name", "rank_waiting_time_only",
                "rank_full_fairness_aware", "shift_full_fairness_aware"]])
    movers.columns = ["Provider", "Specialty", "Rank (waiting-only)", "Rank (fairness-aware)", "Rank improvement"]
    for c in movers.columns[2:]:
        movers[c] = movers[c].astype(int)

    def tbl(df):
        return df.to_html(index=False, classes="tbl", border=0)

    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{l}</div></div>'
        for l, v in kpis)

    pages = {
        "Overview": f'<div class="kpis">{kpi_html}</div>{fig_html(f_trend)}'
                    f'<div class="row">{fig_html(f_spec)}{fig_html(f_prov)}</div>',
        "Ranking": f'<h3>Top 40 priority areas — full fairness-aware model ({latest})</h3>{tbl(rank)}',
        "Fairness": f'{fig_html(f_fair)}{fig_html(f_frprov)}',
        "Operational": f'{fig_html(f_op)}',
        "Simulation": f'{fig_html(f_ov)}'
                      f'<div class="row2"><div><h3>Lifts</h3>{tbl(lift.round(3))}'
                      f'<h3>Sensitivity (top-20 stability)</h3>{tbl(sens.round(2))}</div>'
                      f'<div><h3>Biggest movers under fairness-aware model</h3>{tbl(movers)}</div></div>',
    }
    tabs = "".join(f'<button class="tab{" active" if i==0 else ""}" onclick="show(\'{k}\')">{k}</button>'
                   for i, k in enumerate(pages))
    panes = "".join(f'<div id="{k}" class="pane{" active" if i==0 else ""}">{v}</div>'
                    for i, (k, v) in enumerate(pages.items()))

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>FairQueue Simulator — Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f6f7fb;color:#222}}
 header{{background:#3a0ca3;color:#fff;padding:18px 26px}}
 header h1{{margin:0;font-size:22px}} header p{{margin:4px 0 0;opacity:.85;font-size:14px}}
 .tabs{{display:flex;gap:6px;background:#fff;padding:8px 20px;border-bottom:1px solid #e3e3ef;position:sticky;top:0;z-index:9}}
 .tab{{border:0;background:#eee;padding:9px 16px;border-radius:8px;cursor:pointer;font-size:14px}}
 .tab.active{{background:#4361ee;color:#fff}}
 .pane{{display:none;padding:20px 26px}} .pane.active{{display:block}}
 .kpis{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}}
 .kpi{{background:#fff;border-radius:12px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);min-width:160px}}
 .kpi-v{{font-size:24px;font-weight:700;color:#3a0ca3}} .kpi-l{{font-size:13px;color:#666}}
 .row{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
 .row2{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:10px}}
 .tbl{{border-collapse:collapse;width:100%;background:#fff;font-size:13px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
 .tbl th{{background:#3a0ca3;color:#fff;padding:7px 9px;text-align:left}}
 .tbl td{{padding:6px 9px;border-bottom:1px solid #eee}}
 .tbl tr:nth-child(even){{background:#faf9ff}}
 h3{{color:#3a0ca3}}
</style></head><body>
<header><h1>🏥 FairQueue Simulator — Fairness-aware elective-care prioritisation</h1>
<p>Provider × specialty × month priority scoring · waiting pressure (50%) + fairness risk (30%) + operational pressure (20%) · data {g.month.min()} → {latest}</p></header>
<div class="tabs">{tabs}</div>{panes}
<script>
 function show(id){{document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
  window.dispatchEvent(new Event('resize'));}}
</script></body></html>"""

    out = OUTPUTS / "FairQueue_Dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
