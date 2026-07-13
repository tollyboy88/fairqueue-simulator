import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import plotly.express as px
import data_access as da

st.set_page_config(page_title="Fairness Analysis", page_icon="⚖️", layout="wide")
st.title("⚖️ Fairness Analysis")
st.caption("Fairness gap = share of the longest waits (>52 weeks) minus share of all waits. "
           "Positive = the group is over-represented among the longest waiters.")

det = da.fairness_detail()
if det.empty:
    st.warning("Fairness detail not found. Run `python src/03_clean_wlmds.py`.")
    st.stop()

scr = da.scores()
prov_names = (scr[["provider_code", "provider_name"]].drop_duplicates()
              .set_index("provider_code").provider_name.to_dict())
det = det.copy()
det["provider_name"] = det.provider_code.map(prov_names).fillna(det.provider_code)

c1, c2 = st.columns(2)
metric = c1.selectbox("Demographic dimension", ["IMD", "Ethnicity", "Age", "Sex"])
provs = sorted(p for p in det.provider_name.unique())
default = "WALSALL HEALTHCARE NHS TRUST"
prov = c2.selectbox("Provider", provs,
                    index=provs.index(default) if default in provs else 0)

d = det[(det.metric == metric) & (det.provider_name == prov)].copy()
d = d.sort_values("fairness_gap", ascending=False)
fig = px.bar(d, x="fairness_gap", y="Category", orientation="h",
             color="fairness_gap", color_continuous_scale="RdBu_r",
             title=f"{metric} fairness gaps - {prov.title()}",
             labels={"fairness_gap": "Fairness gap (share long - share all)", "Category": ""})
st.plotly_chart(fig, use_container_width=True)

st.markdown("#### Most over-represented groups in the longest waits (nationally)")
nat = (det.groupby(["metric", "Category"], as_index=False)
       .fairness_gap.mean().sort_values("fairness_gap", ascending=False).head(15))
st.dataframe(nat.rename(columns={"metric": "Dimension", "fairness_gap": "Mean gap"})
             .round({"Mean gap": 3}), use_container_width=True, hide_index=True)

st.markdown("#### Provider fairness-risk scores")
fr = (scr[["provider_name"]].assign(fairness=scr.fairness_risk_score)
      .groupby("provider_name", as_index=False).fairness.mean().nlargest(15, "fairness"))
st.plotly_chart(px.bar(fr, x="fairness", y="provider_name", orientation="h",
                       title="Top 15 providers by fairness-risk score",
                       labels={"fairness": "Fairness-risk score", "provider_name": ""}),
                use_container_width=True)
