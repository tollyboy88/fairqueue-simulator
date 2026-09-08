import streamlit as st

st.title("Methods and limitations")
st.subheader("What the system does")
st.markdown(
    """
1. Builds provider–specialty–month features from public aggregate NHS releases.
2. Predicts the 52-week incomplete-pathway breach rate exactly three reporting months ahead,
   using the RTT publication date as the operational forecast date.
3. Ranks forecast pressure and optionally enforces a minimum share of selected
   provider-specialty services associated with high-equity-need providers.
"""
)
st.subheader("What it does not do")
st.markdown(
    """
- It does not score, schedule, or ration individual patients.
- It does not claim that demographic disparity causes future waiting pressure.
- It does not optimise clinical outcomes, costs, or capacity allocation.
- It has not been prospectively evaluated in an NHS operational workflow.
"""
)
st.subheader("Important limitations")
st.markdown(
    """The observational unit is an aggregated service line, provider coding changes can affect
longitudinal comparability, public operational data are incomplete, and the equity analysis
uses only operational and WLMDS sources published by the relevant RTT forecast date.
Results therefore support monitoring and scenario discussion only."""
)
