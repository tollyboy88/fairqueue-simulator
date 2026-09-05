"""FairQueue 2.0 home page. Run: streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
import data_access as da

st.set_page_config(page_title="FairQueue 2.0", page_icon="🏥", layout="wide")

st.title("FairQueue 2.0")
st.subheader("Forecast first; apply equity constraints explicitly")

st.markdown(
    """
FairQueue forecasts the **provider × specialty 52-week breach rate three months ahead**
from public NHS data. It then selects a top-*K* monitoring list while allowing a decision
maker to set a minimum share of providers with high measured equity need.

The prediction target is independent of the prioritisation policy. Demographic disparities
never enter the forecast; they are applied only in the transparent selection constraint.
The tool prioritises aggregated service pressure, **not individual patients**.
"""
)

try:
    metrics = da.metric("test_model_metrics.csv")
    selected = metrics.loc[metrics.model.eq("Random Forest")].iloc[0]
    predictions = da.predictions()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Held-out observations", f"{len(predictions):,}")
    c2.metric("Test target months", predictions.target_month.nunique())
    c3.metric("RMSE", f"{selected.rmse * 100:.2f} pp")
    c4.metric("Recall@20", f"{selected.recall_at_20:.1%}")
    st.info(
        "Use the sidebar to inspect forecasts, the equity–utility frontier, temporal "
        "validation, and the study's intended-use limits."
    )
except FileNotFoundError:
    st.error("Generated data are missing. Run `py run_all.py --skip-download` first.")

st.caption(
    "Research prototype. Outputs support service-level review and do not make clinical "
    "decisions, allocate treatment, or estimate patient-level risk."
)
