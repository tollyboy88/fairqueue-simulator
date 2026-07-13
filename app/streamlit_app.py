"""
FairQueue Simulator — home page.
Run with:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
import data_access as da

st.set_page_config(page_title="FairQueue Simulator", page_icon="🏥", layout="wide")

st.title("🏥 FairQueue Simulator")
st.subheader("Fairness-aware dynamic elective-care prioritisation")

st.markdown(
    """
A local, **explainable** simulator that ranks NHS **provider × specialty × month**
areas by combining three transparent signals:

- **Waiting-list pressure** — 18 & 52-week breaches, DTA, demand, throughput, backlog growth
- **Fairness risk** — over-representation of deprived / ethnic / age / sex groups in the longest waits
- **Operational pressure** — diagnostics, A&E, beds, theatres and cancelled operations

```
final_priority_score = 0.50 × waiting + 0.30 × fairness + 0.20 × operational   (→ 0–100)
```

It prioritises *areas of pressure*, **not individual patients**, and lets you compare
five prioritisation strategies.
"""
)

try:
    s = da.scores()
    ms = da.months(s)
    latest = ms[-1]
    g = s[s.month == latest]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Provider-specialty areas", f"{g.shape[0]:,}")
    c2.metric("Providers", f"{g.provider_code.nunique():,}")
    c3.metric("Months covered", f"{len(ms)}  ({ms[0]} → {ms[-1]})")
    c4.metric("High/Critical areas (latest)",
              int(g.priority_level.isin(["High", "Critical"]).sum()))
    st.caption("Use the pages in the sidebar: National Overview · Ranking · Fairness · "
               "Operational · Simulation · Explanation.")
except FileNotFoundError:
    st.error("Processed data not found. Run the pipeline first:\n\n"
             "`python src/02_clean_rtt.py … src/07_simulation_engine.py`")
