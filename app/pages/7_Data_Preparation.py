import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import ingest_engine as IE

st.set_page_config(page_title="Data Preparation", page_icon="🧹", layout="wide")
st.title("🧹 Data Preparation — auto clean & join")
st.caption("Upload the raw datasets a provider might hold (RTT, diagnostics, A&E, "
           "cancelled operations…). The engine detects what each file is, cleans it, "
           "and joins them into the project's provider × specialty × month structure — "
           "the same logic used on the data folder.")

up = st.file_uploader("Upload one or more files (Excel / CSV)",
                      type=["xlsx", "xls", "csv"], accept_multiple_files=True)

if not up:
    st.info("Drop in files such as *Incomplete-Provider-…xlsx*, "
            "*Monthly-Diagnostics-…Provider…xls*, *…A&E…csv*, *QMCO-…Cancelled…csv*. "
            "An RTT ‘Incomplete-Provider’ file provides the base grid.")
    st.stop()

files = [(f.name, f) for f in up]
with st.spinner("Detecting, cleaning and joining…"):
    res = IE.ingest(files)

st.subheader("What I detected")
st.dataframe(res["report"], use_container_width=True, hide_index=True)

joined = res["joined"]
if joined is None or joined.empty:
    st.warning("No RTT ‘Incomplete-Provider’ base file detected, so there is no "
               "provider × specialty grid to join onto. Add one and re-upload.")
    st.stop()

st.session_state["prepared_data"] = joined
st.subheader(f"Cleaned & joined dataset — {len(joined):,} rows × {joined.shape[1]} columns")
st.dataframe(joined.head(500), use_container_width=True, height=420, hide_index=True)

c1, c2 = st.columns(2)
c1.download_button("⬇ Download cleaned dataset (CSV)",
                   joined.to_csv(index=False).encode(), "cleaned_joined.csv", "text/csv")
c2.success("Saved in this session — open **Predict & Explain** to score it.")

st.caption("Provider-level sources (diagnostics, A&E, cancellations) are matched by "
           "provider + month and applied across that provider's specialties, exactly as "
           "in the main pipeline. Files whose period can't be read are labelled ‘uploaded’.")
