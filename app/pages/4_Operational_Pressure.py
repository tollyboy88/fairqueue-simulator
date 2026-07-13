import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import plotly.express as px
import data_access as da

st.set_page_config(page_title="Operational Pressure", page_icon="🛠️", layout="wide")
st.title("🛠️ Operational Pressure")
st.caption("Diagnostics · A&E · beds · theatres · cancelled operations, combined into the "
           "operational pressure score (0.25 diagnostic + 0.25 bed + 0.20 A&E + 0.15 cancellation + 0.15 theatre).")

mod = da.modelling()
ms = da.months(mod)
month = st.selectbox("Month", ms, index=len(ms) - 1)
d = mod[mod.month == month]

comp = {
    "Diagnostic >6w (norm)": "diagnostic_bottleneck_n",
    "Bed occupancy (norm)": "bed_pressure_n",
    "A&E pressure (norm)": "ae_pressure_score_n",
    "Cancellation (norm)": "cancellation_pressure_n",
    "Theatre pressure (norm)": "theatre_pressure_n",
}
means = {k: float(d[v].mean()) for k, v in comp.items() if v in d}
st.plotly_chart(
    px.bar(x=list(means.values()), y=list(means.keys()), orientation="h",
           labels={"x": "Mean normalised pressure", "y": ""},
           title=f"Average operational pressure components ({month})"),
    use_container_width=True)

prov = (d.groupby("provider_name", as_index=False)
        .operational_pressure_score.mean().nlargest(15, "operational_pressure_score")
        if "operational_pressure_score" in d.columns else None)
if prov is None:
    sc = da.scores(); sc = sc[sc.month == month]
    prov = (sc.groupby("provider_name", as_index=False)
            .operational_pressure_score.mean().nlargest(15, "operational_pressure_score"))
st.plotly_chart(
    px.bar(prov, x="operational_pressure_score", y="provider_name", orientation="h",
           title=f"Top 15 providers by operational pressure ({month})",
           labels={"operational_pressure_score": "Operational pressure score", "provider_name": ""}),
    use_container_width=True)

st.markdown("#### Provider operational detail")
cols = [c for c in ["provider_name", "diagnostic_over_6w_rate", "bed_occupancy_rate",
                    "ae_4hr_breach_rate", "cancelled_operations", "theatre_daycase_share"]
        if c in mod.columns]
det = (mod[mod.month == month][cols].dropna(how="all", subset=cols[1:])
       .groupby("provider_name", as_index=False).mean().round(3))
st.dataframe(det, use_container_width=True, height=420, hide_index=True)
