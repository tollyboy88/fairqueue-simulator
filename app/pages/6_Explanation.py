import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import plotly.express as px
import pandas as pd
import data_access as da

st.set_page_config(page_title="Explanation", page_icon="🔍", layout="wide")
st.title("🔍 Why is this area high priority?")

scr = da.scores()
ms = da.months(scr)

c1, c2, c3 = st.columns(3)
month = c1.selectbox("Month", ms, index=len(ms) - 1)
d0 = scr[scr.month == month]
provs = sorted(d0.provider_name.dropna().unique())
default = "WALSALL HEALTHCARE NHS TRUST"
prov = c2.selectbox("Provider", provs, index=provs.index(default) if default in provs else 0)
specs = sorted(d0[d0.provider_name == prov].treatment_function_name.dropna().unique())
spec = c3.selectbox("Specialty", specs)

row = d0[(d0.provider_name == prov) & (d0.treatment_function_name == spec)]
if row.empty:
    st.stop()
r = row.iloc[0]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Priority score", f"{r.priority_score_100:.1f}")
m2.metric("Priority level", r.priority_level)
m3.metric("Waiting / Fairness / Operational",
          f"{r.waiting_pressure_score:.2f} / {r.fairness_risk_score:.2f} / {r.operational_pressure_score:.2f}")
rank = int(d0.priority_score_100.rank(ascending=False, method="min")[row.index[0]])
m4.metric("National rank (month)", f"{rank} / {len(d0):,}")

# decompose contributions to the 0-100 score
DRIVERS = [
    ("18-week breach rate", "breach_18w_rate_n", 0.50 * 0.30),
    ("52-week long-wait rate", "breach_52w_rate_n", 0.50 * 0.25),
    ("DTA pressure", "dta_pressure_n", 0.50 * 0.15),
    ("Backlog growth", "backlog_growth_rate_n", 0.50 * 0.15),
    ("Demand pressure", "demand_pressure_n", 0.50 * 0.10),
    ("Low throughput", "inverse_throughput_n", 0.50 * 0.05),
    ("Deprivation over-representation", "fairness_deprivation_score_n", 0.30 * 0.30),
    ("Ethnicity over-representation", "fairness_ethnicity_score_n", 0.30 * 0.25),
    ("Age over-representation", "fairness_age_score_n", 0.30 * 0.20),
    ("Sex imbalance", "fairness_sex_score_n", 0.30 * 0.15),
    ("Missing demographics", "missing_demographic_score_n", 0.30 * 0.10),
    ("Diagnostic bottleneck", "diagnostic_bottleneck_n", 0.20 * 0.25),
    ("Bed occupancy", "bed_pressure_n", 0.20 * 0.25),
    ("A&E pressure", "ae_pressure_score_n", 0.20 * 0.20),
    ("Cancellation pressure", "cancellation_pressure_n", 0.20 * 0.15),
    ("Theatre pressure", "theatre_pressure_n", 0.20 * 0.15),
]
rows = [{"Driver": lbl, "Contribution": (r[col] * w * 100) if col in row.columns else 0.0}
        for lbl, col, w in DRIVERS]
contrib = pd.DataFrame(rows).sort_values("Contribution", ascending=False)

st.markdown("#### Main drivers of the priority score")
st.plotly_chart(
    px.bar(contrib.head(8).iloc[::-1], x="Contribution", y="Driver", orientation="h",
           title="Top contributors (points out of 100)",
           labels={"Contribution": "Points contributed", "Driver": ""}),
    use_container_width=True)

top = contrib.head(5).Driver.tolist()
st.markdown("**In words:** this area scores **{:.1f}/100** ({}). The biggest drivers are: {}."
            .format(r.priority_score_100, r.priority_level,
                    ", ".join(f"{i+1}. {t}" for i, t in enumerate(top))))

st.markdown("#### Underlying RTT figures")
st.dataframe(row[["incomplete_total", "breach_18w_count", "breach_52w_count",
                  "dta_total", "new_rtt_total", "admitted_total", "non_admitted_total"]]
             .T.rename(columns={row.index[0]: "value"}), use_container_width=True)
