import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import plotly.express as px
import data_access as da

st.set_page_config(page_title="National Overview", page_icon="📈", layout="wide")
st.title("📈 National Overview")

rtt = da.rtt()
scr = da.scores()
g = rtt.groupby("month", as_index=False).agg(
    incomplete=("incomplete_total", "sum"),
    b18=("breach_18w_count", "sum"), b52=("breach_52w_count", "sum"),
    dta=("dta_total", "sum"), new=("new_rtt_total", "sum"))
g["pct_within_18w"] = 100 * (1 - g.b18 / g.incomplete)
latest = g.month.max()
lr = g[g.month == latest].iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Incomplete pathways", f"{lr.incomplete/1e6:.2f} m")
c2.metric("% within 18 weeks", f"{lr.pct_within_18w:.1f}%")
c3.metric("Waiting >52 weeks", f"{lr.b52/1e3:,.0f} k")
c4.metric("New RTT demand (month)", f"{lr.new/1e6:.2f} m")

st.plotly_chart(
    px.line(g, x="month", y=["incomplete", "b18", "b52"], markers=True,
            labels={"value": "Patients", "month": "Month", "variable": "Measure"},
            title="National RTT waiting-list trend, 2025/26"),
    use_container_width=True)

col1, col2 = st.columns(2)
sp = (scr[scr.month == latest].groupby("treatment_function_name", as_index=False)
      .waiting_pressure_score.mean().nlargest(10, "waiting_pressure_score"))
col1.plotly_chart(
    px.bar(sp, x="waiting_pressure_score", y="treatment_function_name", orientation="h",
           title=f"Top 10 pressured specialties ({latest})",
           labels={"waiting_pressure_score": "Mean waiting-pressure", "treatment_function_name": ""}),
    use_container_width=True)
pp = (scr[scr.month == latest].groupby("provider_name", as_index=False)
      .priority_score_100.mean().nlargest(10, "priority_score_100"))
col2.plotly_chart(
    px.bar(pp, x="priority_score_100", y="provider_name", orientation="h",
           title=f"Top 10 pressured providers ({latest})",
           labels={"priority_score_100": "Mean priority score", "provider_name": ""}),
    use_container_width=True)
