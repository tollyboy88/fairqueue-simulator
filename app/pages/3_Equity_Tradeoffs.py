import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import data_access as da

st.title("Equity–pressure-capture frontier")
st.caption(
    "Top-20 June 2026 provider-specialty service list using the latest WLMDS evidence "
    "available by the 31 March 2026 decision date. High equity need means the associated "
    "provider is in the top quartile for at least one disparity dimension."
)
tradeoff = da.metric("equity_pressure_capture_frontier.csv")
frontier = tradeoff[tradeoff.strategy.eq("Equity-constrained primary forecast")].copy()
fig = px.line(
    frontier, x="high_equity_need_service_share", y="recall_at_20", markers=True,
    hover_data=["minimum_high_need_share", "observed_pressure_mean"],
)
fig.update_layout(
    xaxis_tickformat=".0%", yaxis_tickformat=".0%",
    xaxis_title="Selected services associated with high-need providers",
    yaxis_title="Recall of observed top-20 pressure",
)
st.plotly_chart(fig, use_container_width=True)
floor = st.select_slider("Minimum high-need share", options=frontier.minimum_high_need_share.tolist())
selected = da.selections()
selected = selected[selected.strategy.eq("Equity-constrained primary forecast") & selected.minimum_high_need_share.eq(floor)]
primary = da.specification()["primary_forecaster"]
table = selected[["provider_name", "treatment_function_name", primary, "high_equity_need"]]
st.dataframe(table.rename(columns={primary: "forecast"}).style.format({"forecast": "{:.2%}"}), use_container_width=True, hide_index=True)
st.subheader("Provider-specialty cap sensitivity")
st.dataframe(da.metric("provider_cap_sensitivity.csv"), use_container_width=True, hide_index=True)
st.warning("This frontier is a retrospective policy illustration, not evidence of causal benefit.")
