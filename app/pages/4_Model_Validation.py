import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import data_access as da

st.title("Temporal validation")
st.markdown(
    "Models were selected on January–June 2025 targets and evaluated once on "
    "October 2025–June 2026 targets. Preprocessing is fitted on training data only."
)
metrics = da.metric("test_model_metrics.csv")
specification = da.specification()
st.info(
    f"{specification['primary_forecaster']} is the primary forecaster because it had the "
    f"lowest validation MAE. {specification['selected_learned_model']} is the selected "
    "learned comparator."
)
fig = px.scatter(metrics, x="rmse", y="recall_at_20", color="model", text="model")
fig.update_traces(textposition="top center")
fig.update_layout(xaxis_title="RMSE (lower is better)", yaxis_title="Recall@20 (higher is better)")
st.plotly_chart(fig, use_container_width=True)
st.subheader("Feature-set ablation")
st.dataframe(da.metric("ablation_results.csv").round(4), use_container_width=True, hide_index=True)
st.subheader("Paired provider bootstrap")
st.dataframe(da.metric("paired_bootstrap_differences.csv").round(5), use_container_width=True, hide_index=True)
st.caption(
    "Lagged operational indicators did not materially improve aggregate point accuracy; "
    "this negative result is retained rather than hidden."
)
