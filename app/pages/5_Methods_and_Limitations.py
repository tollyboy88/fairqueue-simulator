import streamlit as st

st.title("Methods and limitations")
st.subheader("What the system does")
st.markdown(
    """
1. Builds provider–specialty–month features from public aggregate NHS releases.
2. Predicts the 52-week incomplete-pathway breach rate exactly three months ahead.
3. Ranks forecast pressure and optionally enforces a minimum representation floor for
   providers with high measured equity need.
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
uses one nationally available WLMDS snapshot. Results therefore support monitoring and
scenario discussion only."""
)
