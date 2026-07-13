import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import data_access as da

st.set_page_config(page_title="Provider-Specialty Ranking", page_icon="🏆", layout="wide")
st.title("🏆 Provider × Specialty Ranking")

scr = da.scores()
ms = da.months(scr)

c1, c2, c3 = st.columns(3)
month = c1.selectbox("Month", ms, index=len(ms) - 1)
levels = c2.multiselect("Priority level", ["Critical", "High", "Moderate", "Lower"],
                        default=["Critical", "High", "Moderate", "Lower"])
specs = ["(all)"] + sorted(scr.treatment_function_name.dropna().unique())
spec = c3.selectbox("Specialty", specs)

prov = st.text_input("Provider name contains", "")

d = scr[(scr.month == month) & (scr.priority_level.isin(levels))].copy()
if spec != "(all)":
    d = d[d.treatment_function_name == spec]
if prov.strip():
    d = d[d.provider_name.str.contains(prov.strip(), case=False, na=False)]

d = d.sort_values("priority_score_100", ascending=False)
d.insert(0, "rank", range(1, len(d) + 1))
show = d[["rank", "provider_name", "treatment_function_name",
          "waiting_pressure_score", "fairness_risk_score", "operational_pressure_score",
          "priority_score_100", "priority_level"]].rename(columns={
    "provider_name": "Provider", "treatment_function_name": "Specialty",
    "waiting_pressure_score": "Waiting", "fairness_risk_score": "Fairness",
    "operational_pressure_score": "Operational", "priority_score_100": "Priority (0-100)",
    "priority_level": "Level"})

st.caption(f"{len(show):,} areas - {month}")
st.dataframe(
    show.round({"Waiting": 2, "Fairness": 2, "Operational": 2, "Priority (0-100)": 1}),
    use_container_width=True, height=560, hide_index=True,
    column_config={"Priority (0-100)": st.column_config.ProgressColumn(
        "Priority (0-100)", min_value=0, max_value=100, format="%.1f")})

st.download_button("Download this ranking (CSV)",
                   show.to_csv(index=False).encode(), f"ranking_{month}.csv", "text/csv")
