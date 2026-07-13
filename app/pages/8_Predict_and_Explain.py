import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import predictor as P
import data_access as da

st.set_page_config(page_title="Predict & Explain", page_icon="🤖", layout="wide")
st.title("🤖 Predict & Explain — fairness-aware priority")
st.caption("Predicts the fairness-aware elective-care priority for a provider × specialty "
           "area, with an explainable-AI breakdown and a bias/fairness audit. Fairness "
           "enters only as aggregate over-representation gaps — never raw group identity.")

bundle = P.load_model()
m = bundle["metrics"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Model R²", f"{m['r2']:.3f}")
c2.metric("Mean abs. error", f"{m['mae']:.2f} pts")
c3.metric("Level accuracy", f"{m['level_accuracy']:.1%}")
c4.metric("Training rows", f"{m['n_train']:,}")

imp = (pd.DataFrame({"feature": list(bundle["importances"]),
                     "importance": list(bundle["importances"].values())})
       .assign(label=lambda d: d.feature.map(P.FEATURE_LABELS))
       .sort_values("importance", ascending=True).tail(10))
st.plotly_chart(px.bar(imp, x="importance", y="label", orientation="h",
                       title="What drives the model (global feature importance)",
                       labels={"importance": "Relative importance", "label": ""}),
                use_container_width=True)

# ---------------- choose data to score ----------------
st.markdown("### 1 · Choose data to score")
choice = st.radio("Source", ["Prepared data (from Data Preparation page)",
                             "Upload a file (Excel / CSV)", "Sample of the project data"],
                  horizontal=True)
df_in = None
if choice.startswith("Prepared"):
    df_in = st.session_state.get("prepared_data")
    if df_in is None:
        st.info("No prepared data yet — use the **Data Preparation** page first, or pick another source.")
elif choice.startswith("Upload"):
    f = st.file_uploader("Feature table (rows = provider-specialty areas)", type=["xlsx", "xls", "csv"])
    if f is not None:
        df_in = P.read_tabular(f, f.name)
else:
    samp = da.modelling().sample(300, random_state=1)
    df_in = samp

if df_in is None:
    st.stop()

feats = P.align_features(df_in)
cov = feats[P.FEATURES].notna().mean().mean()
st.caption(f"Matched {int((feats[P.FEATURES].notna().any()).sum())}/{len(P.FEATURES)} "
           f"model features · {cov:.0%} of cells populated (missing are imputed).")

# ---------------- optional rubric ----------------
st.markdown("### 2 · Optional rubric / feature weights (Word .docx)")
rub = st.file_uploader("A .docx listing `feature: weight` rows or a 2-column table", type=["docx"])
weights = {}
if rub is not None:
    weights = P.parse_rubric_docx(rub)
    if weights:
        st.success("Rubric weights read: " + ", ".join(
            f"{P.FEATURE_LABELS.get(k, k)}={v}" for k, v in weights.items()))
    else:
        st.warning("No recognisable feature weights found in the document.")

# ---------------- predict ----------------
pred = P.predict(bundle, feats)
contrib = P.local_contributions(bundle, feats)
if weights:
    pred["rubric_score"] = P.apply_rubric(feats, weights)

idcols = [c for c in ["month", "provider_name", "treatment_function_name"] if c in pred.columns]
st.markdown("### 3 · Predictions")
showcols = idcols + ["predicted_priority_score", "predicted_level"] + (["rubric_score"] if weights else [])
st.dataframe(pred[showcols].sort_values("predicted_priority_score", ascending=False)
             .head(300), use_container_width=True, height=380, hide_index=True)
st.download_button("⬇ Download predictions (CSV)",
                   pred[showcols].to_csv(index=False).encode(), "predictions.csv", "text/csv")

# ---------------- per-area explanation ----------------
st.markdown("### 4 · Why this prediction? (explainable AI)")
order = pred.sort_values("predicted_priority_score", ascending=False).index.tolist()
def _lab(i):
    r = pred.loc[i]
    nm = r.get("provider_name", f"row {i}"); sp = r.get("treatment_function_name", "")
    return f"{nm} — {sp}  ({r.predicted_priority_score:.1f})"
pick = st.selectbox("Area", order[:200], format_func=_lab)
pos = pred.index.get_loc(pick) if pick in pred.index else 0
row = contrib.iloc[pos]
drivers = P.top_drivers(row, k=6)
dd = pd.DataFrame(drivers, columns=["Driver", "Contribution (pts)"]).iloc[::-1]
st.plotly_chart(px.bar(dd, x="Contribution (pts)", y="Driver", orientation="h",
                       title="Top contributors to this prediction (points out of 100)"),
                use_container_width=True)
st.markdown("**In words:** " + _lab(pick) + ". Main drivers — " +
            ", ".join(f"{d} (+{v})" for d, v in drivers) + ".")

# ---------------- fairness / bias audit ----------------
st.markdown("### 5 · Fairness & bias audit")
audit = P.fairness_audit(pred)
ac = pd.DataFrame({"Fairness signal": list(audit["correlations"]),
                   "Corr. with predicted priority": list(audit["correlations"].values())})
st.dataframe(ac, use_container_width=True, hide_index=True)
if "priority_by_deprivation_tercile" in audit:
    st.write("Mean predicted priority by deprivation tercile:",
             audit["priority_by_deprivation_tercile"])
flag = audit.get("bias_flag")
if flag is False:
    st.success("No deprivation bias detected — higher-deprivation areas are not under-prioritised.")
elif flag:
    st.warning("⚠ Possible bias: higher-deprivation areas under-prioritised.")
else:
    st.info("Deprivation audit not available for this data.")
for n in audit["notes"]:
    st.caption("• " + n)

# ---------------- comprehensive report ----------------
def build_report():
    rows = "".join(
        f"<tr><td>{pred.loc[i].get('provider_name','')}</td>"
        f"<td>{pred.loc[i].get('treatment_function_name','')}</td>"
        f"<td>{pred.loc[i].predicted_priority_score:.1f}</td>"
        f"<td>{pred.loc[i].predicted_level}</td>"
        f"<td>{'; '.join(f'{d} (+{v})' for d,v in P.top_drivers(contrib.loc[pred.index.get_loc(i)],3))}</td></tr>"
        for i in order[:25])
    corr = "".join(f"<li>{k}: {v:+.3f}</li>" for k, v in audit["correlations"].items())
    impr = "".join(f"<li>{P.FEATURE_LABELS[f]}: {w:.1%}</li>"
                   for f, w in sorted(bundle["importances"].items(), key=lambda x: -x[1])[:8])
    return f"""<!doctype html><meta charset='utf-8'><title>FairQueue XAI report</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#222;max-width:1000px}}
h1,h2{{color:#3a0ca3}} table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{background:#3a0ca3;color:#fff;padding:6px;text-align:left}} td{{border-bottom:1px solid #eee;padding:6px}}</style>
<h1>FairQueue — Explainable-AI prediction report</h1>
<p>Model: RandomForest · R²={m['r2']:.3f} · MAE={m['mae']:.2f} pts · level accuracy {m['level_accuracy']:.1%}.
Unit of prediction: provider × specialty area (not individual patients).</p>
<h2>How the prediction is made</h2>
<p>The model predicts a 0–100 fairness-aware priority from real-world features (waiting
breaches, DTA, demand, throughput, backlog, fairness gaps, diagnostics, beds, A&E,
cancellations, theatres). Local explanations use drop-to-median attribution: each
feature's contribution is how much the prediction changes when that feature is reset to
its typical value.</p>
<h2>Global drivers</h2><ul>{impr}</ul>
<h2>Fairness without bias</h2>
<p>Protected characteristics are used only as aggregate over-representation gaps, never as
raw group identity. Correlation of each fairness gap with predicted priority (positive =
equity-promoting):</p><ul>{corr}</ul>
<p>Deprivation audit: {audit.get('priority_by_deprivation_tercile','n/a')} · bias flag: {audit.get('bias_flag')}.</p>
<h2>Top predicted areas</h2>
<table><tr><th>Provider</th><th>Specialty</th><th>Priority</th><th>Level</th><th>Main drivers</th></tr>{rows}</table>
"""

st.download_button("⬇ Download comprehensive XAI report (HTML)",
                   build_report().encode(), "fairqueue_xai_report.html", "text/html")
