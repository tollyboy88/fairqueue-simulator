import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import plotly.express as px
import data_access as da

st.set_page_config(page_title="Simulation Comparison", page_icon="🔀", layout="wide")
st.title("🔀 Simulation: comparing prioritisation strategies")

sc = da.strategies()
ms = da.months(sc)
month = st.selectbox("Month", ms, index=len(ms) - 1)
d = sc[sc.month == month].copy()

ov = da.metric_csv("strategy_metrics.csv")
lift = da.metric_csv("fairness_lift_results.csv")
sens = da.metric_csv("sensitivity_analysis.csv")

st.markdown("#### How much does each strategy change the top-20 vs waiting-time only?")
if not ov.empty:
    o = ov[ov.month == month].copy()
    o["strategy"] = o.strategy.map(da.STRATEGY_LABELS).fillna(o.strategy)
    st.plotly_chart(
        px.bar(o.sort_values("top20_overlap_with_waiting_only"),
               x="top20_overlap_with_waiting_only", y="strategy", orientation="h",
               range_x=[0, 1], title=f"Top-20 overlap with waiting-time only ({month})",
               labels={"top20_overlap_with_waiting_only": "Shared share of top-20", "strategy": ""}),
        use_container_width=True)
    st.caption("Lower overlap = the strategy meaningfully changes which areas are prioritised.")

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Lifts (latest month)")
    if not lift.empty:
        st.dataframe(lift.assign(value=lift.value.round(3)).rename(
            columns={"metric": "Metric", "value": "Lift"}),
            use_container_width=True, hide_index=True)
with c2:
    st.markdown("#### Sensitivity — top-20 stability")
    if not sens.empty:
        st.dataframe(sens.rename(columns={
            "scenario": "Scenario", "weights_w_f_o": "Weights (W/F/O)",
            "overlap_with_main_top20": "Overlap w/ main"}).round(2),
            use_container_width=True, hide_index=True)

st.markdown("#### Biggest movers under the full fairness-aware model")
st.caption("Areas that rise most when fairness & operational pressure are included.")
movers = d.nlargest(15, "shift_full_fairness_aware")[
    ["provider_name", "treatment_function_name", "rank_waiting_time_only",
     "rank_full_fairness_aware", "shift_full_fairness_aware"]].rename(columns={
        "provider_name": "Provider", "treatment_function_name": "Specialty",
        "rank_waiting_time_only": "Rank (waiting-only)",
        "rank_full_fairness_aware": "Rank (fairness-aware)",
        "shift_full_fairness_aware": "Rank improvement"})
st.dataframe(movers, use_container_width=True, hide_index=True)

st.markdown("#### Strategy score correlation")
strat_cols = [f"score_{s}" for s in da.STRATEGY_LABELS]
corr = d[strat_cols].corr()
corr.index = [da.STRATEGY_LABELS[c.replace("score_", "")] for c in corr.index]
corr.columns = corr.index
st.plotly_chart(px.imshow(corr, text_auto=".2f", color_continuous_scale="Blues",
                          title="Correlation between strategy scores"),
                use_container_width=True)
