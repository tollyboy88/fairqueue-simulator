import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import data_access as da

st.title("Held-out forecast overview")
st.caption("Feature months July 2025–March 2026; target months October 2025–June 2026.")
monthly = da.metric("monthly_test_metrics.csv")
models = st.multiselect("Models", monthly.model.unique(), default=["Random Forest", "Persistence"])
metric = st.selectbox("Metric", ["rmse", "mae", "r2", "recall_at_20", "ndcg_at_20"])
shown = monthly[monthly.model.isin(models)]
fig = px.line(shown, x="target_month", y=metric, color="model", markers=True)
fig.update_layout(xaxis_title="Target month", yaxis_title=metric.replace("_", " ").upper())
st.plotly_chart(fig, use_container_width=True)
st.dataframe(da.metric("test_model_metrics.csv").round(4), use_container_width=True, hide_index=True)
