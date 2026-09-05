import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import data_access as da

st.title("Equity–utility trade-off")
st.caption(
    "Top-20 June 2026 monitoring list. High equity need means a provider is in the top "
    "quartile for at least one WLMDS disparity dimension."
)
tradeoff = da.metric("equity_utility_tradeoff.csv")
frontier = tradeoff[tradeoff.strategy.eq("Equity-constrained forecast")].copy()
fig = px.line(
    frontier, x="high_equity_need_share", y="recall_at_20", markers=True,
    hover_data=["minimum_high_need_share", "observed_pressure_mean"],
)
fig.update_layout(
    xaxis_tickformat=".0%", yaxis_tickformat=".0%",
    xaxis_title="High-equity-need share in selected list",
    yaxis_title="Recall of observed top-20 pressure",
)
st.plotly_chart(fig, use_container_width=True)
floor = st.select_slider("Minimum high-need share", options=frontier.minimum_high_need_share.tolist())
selected = da.selections()
selected = selected[selected.strategy.eq("Equity-constrained forecast") & selected.minimum_high_need_share.eq(floor)]
table = selected[["provider_name", "treatment_function_name", "Random Forest", "high_equity_need"]]
st.dataframe(table.rename(columns={"Random Forest": "forecast"}).style.format({"forecast": "{:.2%}"}), use_container_width=True, hide_index=True)
st.warning("This frontier is a retrospective policy illustration, not evidence of causal benefit.")
