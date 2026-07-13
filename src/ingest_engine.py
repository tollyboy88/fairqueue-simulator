"""
ingest_engine.py
----------------
Auto-ingest: when a provider uploads several raw datasets (Excel / CSV / xls),
detect what each file is, clean it, and join everything into the project's
provider x specialty x month structure — the same logic the pipeline applies to
the data folder, but on arbitrary uploads.

Public API:
    classify(name, df)      -> source key
    ingest(files)           -> dict(report, joined, rtt, operational, fairness)
where `files` is a list of (name, file_like).
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

# ---- source signatures: filename keyword -> source key
NAME_RULES = [
    ("incomplete-provider", "rtt_incomplete"), ("incomplete_provider", "rtt_incomplete"),
    ("admitted-provider", "rtt_admitted"), ("nonadmitted-provider", "rtt_nonadmitted"),
    ("non-admitted-provider", "rtt_nonadmitted"),
    ("new-periods-provider", "rtt_new"),
    ("diagnostic", "diagnostics"), ("dm01", "diagnostics"),
    ("ae-", "ae"), ("a&e", "ae"), ("ecds", "ae"),
    ("beds-open", "beds"), ("kh03", "beds"),
    ("operating-theatres", "theatres"),
    ("cancelled", "cancelled"), ("qmco", "cancelled"),
    ("wlmds-demographics-geography", "wlmds"),
]
# header-signature fallback: column marker -> source key
HEADER_MARKERS = {
    "Total number of incomplete pathways": "rtt_incomplete",
    "Number waiting 6+ Weeks": "diagnostics",
    "A&E attendances Type 1": "ae",
    "Cancelled Operations": "cancelled",
}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _month(name: str):
    t = name.lower()
    m = re.search(r"(20\d{2})[-_](0[1-9]|1[0-2])", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-_]*(20\d{2})", t)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\d{2})", t)
    if m:
        return f"20{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    return "uploaded"


def _read_raw(file, name):
    n = name.lower()
    if n.endswith(".csv"):
        return pd.read_csv(file, header=None)
    return pd.read_excel(file, header=None, sheet_name=0)


def _find_header(raw, markers=("Provider Code", "Org Code", "Organisation Code", "Code")):
    for r in range(min(25, len(raw))):
        vals = [str(v).strip() for v in raw.iloc[r].tolist()]
        if any(mk in vals for mk in markers):
            return r
    return 0


def _framed(raw):
    """Turn a header-less raw sheet into a proper DataFrame using the detected header row."""
    hr = _find_header(raw)
    df = raw.iloc[hr + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[hr].tolist()]
    return df.reset_index(drop=True)


def classify(name, framed):
    low = name.lower()
    for kw, src in NAME_RULES:
        if kw in low:
            return src
    cols = set(framed.columns)
    for mk, src in HEADER_MARKERS.items():
        if mk in cols:
            return src
    return "unknown"


# ---------------- per-source cleaners (operate on a framed DataFrame) ----------
def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _clean_rtt_incomplete(df, month):
    d = df.rename(columns={"Provider Code": "provider_code", "Provider Name": "provider_name",
                           "Treatment Function Code": "treatment_function_code",
                           "Treatment Function": "treatment_function_name",
                           "Total number of incomplete pathways": "incomplete_total",
                           "Total within 18 weeks": "total_within_18w",
                           "Total 52 plus weeks": "breach_52w_count"})
    d = d[d["provider_code"].notna()]
    d = d[~d["treatment_function_code"].astype(str).str.upper().isin(["C_999", "999", "TOTAL"])]
    for c in ["incomplete_total", "total_within_18w", "breach_52w_count"]:
        d[c] = _num(d.get(c))
    d["breach_18w_count"] = (d.incomplete_total - d.total_within_18w).clip(lower=0)
    d["month"] = month
    return d[["month", "provider_code", "provider_name", "treatment_function_code",
              "treatment_function_name", "incomplete_total", "breach_18w_count",
              "breach_52w_count"]]


def _clean_diag(df, month):
    d = df.rename(columns={"Provider Code": "provider_code",
                           "Total Waiting List": "diag_total",
                           "Number waiting 6+ Weeks": "diag_6w"})
    d = d[d["provider_code"].notna()]
    d = d[~d["provider_code"].astype(str).str.lower().isin(["total", "nan"])]
    d["diagnostic_over_6w_rate"] = _num(d.get("diag_6w")) / _num(d.get("diag_total")).replace(0, np.nan)
    d["month"] = month
    return d[["month", "provider_code", "diagnostic_over_6w_rate"]].dropna()


def _clean_ae(df, month):
    d = df.copy()
    d.columns = [str(c).strip() for c in d.columns]
    oc = "Org Code" if "Org Code" in d.columns else None
    if not oc:
        return pd.DataFrame()
    att = d.filter(regex=r"^A&E attendances (Type|Other)").apply(_num).sum(axis=1)
    over = d.filter(regex=r"^Attendances over 4hrs (Type|Other)").apply(_num).sum(axis=1)
    em = d.filter(regex=r"^Emergency admissions via A&E").apply(_num).sum(axis=1)
    out = pd.DataFrame({"provider_code": d[oc].astype(str).str.strip(), "month": month,
                        "ae_4hr_breach_rate": over / att.replace(0, np.nan),
                        "emergency_admission_rate": em / att.replace(0, np.nan)})
    return out.dropna(subset=["provider_code"])


def _clean_cancelled(df, month):
    d = df.rename(columns={"Org Code": "provider_code",
                           "Cancelled Operations": "cancelled_operations",
                           "Breaches Of Standard": "cancel_28day_breaches"})
    if "provider_code" not in d.columns:
        return pd.DataFrame()
    d["provider_code"] = d["provider_code"].astype(str).str.strip()
    d = d[d.provider_code.str.len() == 3]
    d["cancelled_operations"] = _num(d.get("cancelled_operations"))
    d["cancel_28day_breaches"] = _num(d.get("cancel_28day_breaches"))
    d["month"] = month
    return d[["month", "provider_code", "cancelled_operations", "cancel_28day_breaches"]]


def ingest(files):
    report, rtt, ops, fair = [], [], [], []
    for name, fh in files:
        try:
            raw = _read_raw(fh, name)
            framed = _framed(raw)
            src = classify(name, framed)
            month = _month(name)
            rows = 0
            if src == "rtt_incomplete":
                t = _clean_rtt_incomplete(framed, month); rtt.append(t); rows = len(t)
            elif src == "diagnostics":
                t = _clean_diag(framed, month); ops.append(t); rows = len(t)
            elif src == "ae":
                t = _clean_ae(framed, month); ops.append(t); rows = len(t)
            elif src == "cancelled":
                t = _clean_cancelled(framed, month); ops.append(t); rows = len(t)
            else:
                rows = 0
            report.append({"file": name, "detected": src, "period": month, "rows_out": rows})
        except Exception as e:  # noqa
            report.append({"file": name, "detected": "error", "period": "-", "rows_out": str(e)[:60]})

    rep = pd.DataFrame(report)
    base = pd.concat(rtt, ignore_index=True) if rtt else pd.DataFrame()
    joined = base.copy()
    if not base.empty:
        joined["breach_18w_rate"] = base.breach_18w_count / base.incomplete_total.replace(0, np.nan)
        joined["breach_52w_rate"] = base.breach_52w_count / base.incomplete_total.replace(0, np.nan)
        for t in ops:
            keys = [k for k in ["provider_code", "month"] if k in t.columns]
            if keys and not t.empty:
                joined = joined.merge(t, on=keys, how="left")
    return {"report": rep, "joined": joined,
            "rtt": base, "operational": ops}
