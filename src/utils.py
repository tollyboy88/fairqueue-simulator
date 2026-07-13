"""
utils.py — shared helpers for the FairQueue Simulator pipeline.
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

# ---------------------------------------------------------------- calendar
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def month_to_quarter(month: int) -> str:
    """NHS financial-year quarter (Q1 = Apr-Jun ... Q4 = Jan-Mar)."""
    if month in (4, 5, 6):
        return "Q1"
    if month in (7, 8, 9):
        return "Q2"
    if month in (10, 11, 12):
        return "Q3"
    return "Q4"


def financial_year(year: int, month: int) -> str:
    """Return e.g. '2025/26' for any month in that NHS financial year."""
    if month >= 4:
        return f"{year}/{str(year + 1)[-2:]}"
    return f"{year - 1}/{str(year)[-2:]}"


def period_from_text(text: str):
    """Best-effort (year, month) extraction from a filename or folder name.
    Returns (year:int, month:int|None) or (None, None)."""
    t = text.lower()
    # 'YYYY-MM'
    m = re.search(r"(20\d{2})[-_](0[1-9]|1[0-2])", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    # 'Month YYYY' or 'Mon-YYYY' or 'MonYY'
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[\s\-_]*?(20\d{2})", t)
    if m:
        return int(m.group(2)), _MONTHS[m.group(1)]
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)(\d{2})\b", t)
    if m:
        return 2000 + int(m.group(2)), _MONTHS[m.group(1)]
    m = re.search(r"\b(20\d{2})\b", t)
    if m:
        return int(m.group(1)), None
    return None, None


# ---------------------------------------------------------------- excel reading
def find_header_row(ws, marker="Provider Code", max_scan=30):
    """Locate the 1-based header row that contains `marker` in the first cols."""
    for r in range(1, max_scan + 1):
        rowvals = [ws.cell(row=r, column=c).value for c in range(1, 10)]
        if marker in rowvals:
            return r
    return None


def is_total_tfc(code, name) -> bool:
    """True if a treatment-function row is an aggregate total, not a specialty."""
    code = str(code).strip().upper() if code is not None else ""
    name = str(name).strip().lower() if name is not None else ""
    return code in {"C_999", "999", "TOTAL"} or name == "total"


# ---------------------------------------------------------------- scoring maths
def winsorise(s: pd.Series, lower=0.01, upper=0.99) -> pd.Series:
    lo, hi = s.quantile(lower), s.quantile(upper)
    return s.clip(lo, hi)


def minmax(s: pd.Series) -> pd.Series:
    """Min-max normalise to 0..1; constant series -> 0."""
    s = s.astype(float)
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def safe_div(a, b):
    return np.where((b == 0) | pd.isna(b), 0.0, a / b)


def priority_level(score_100: float) -> str:
    if score_100 >= 80:
        return "Critical"
    if score_100 >= 60:
        return "High"
    if score_100 >= 40:
        return "Moderate"
    return "Lower"
