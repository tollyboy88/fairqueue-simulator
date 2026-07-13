"""
04_clean_operational.py
-----------------------
Clean the five operational-pressure sources into provider x month tables and
combine them. Resumable: each source is cached under
data/interim/operational_cleaned/<source>.parquet and skipped if present.

Sources & signals (raw rates/counts; normalisation happens in 05_build_features):
    diagnostics  -> diagnostic_over_6w_rate          (DM01 Provider)
    ae_emergency -> ae_4hr_breach_rate, emergency_admission_rate, ae_dta_delay_rate
    beds_kh03    -> bed_occupancy_rate               (quarterly -> month)
    theatres     -> theatre_daycase_share            (quarterly -> month)
    cancelled    -> cancelled_operations, cancel_28day_breaches  (quarterly -> month)

Output:
    data/processed/operational_pressure.parquet   (one row per provider x month)
"""
from pathlib import Path
import sys, glob, warnings
import pandas as pd

warnings.simplefilter("ignore")
sys.path.append(str(Path(__file__).resolve().parent))
from utils import RAW, INTERIM, PROCESSED, period_from_text, month_to_quarter  # noqa

OUT = INTERIM / "operational_cleaned"
OUT.mkdir(parents=True, exist_ok=True)
FY_MONTHS = [f"2025-{m:02d}" for m in range(4, 13)] + [f"2026-{m:02d}" for m in range(1, 4)]


def _months_in_quarter(q: str) -> list:
    return {"Q1": ["2025-04", "2025-05", "2025-06"],
            "Q2": ["2025-07", "2025-08", "2025-09"],
            "Q3": ["2025-10", "2025-11", "2025-12"],
            "Q4": ["2026-01", "2026-02", "2026-03"]}[q]


# ---------------------------------------------------------------- A&E
def clean_ae():
    rows = []
    for f in glob.glob(str(RAW / "ae_emergency" / "**" / "*.csv"), recursive=True):
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if "Org Code" not in d.columns:
            continue
        y, m = period_from_text(Path(f).name)
        month = f"{y}-{m:02d}" if (y and m) else None
        if month not in FY_MONTHS:
            continue
        d.columns = [c.strip() for c in d.columns]
        att = d.filter(regex=r"^A&E attendances (Type|Other)").apply(pd.to_numeric, errors="coerce").sum(axis=1)
        over4 = d.filter(regex=r"^Attendances over 4hrs (Type|Other)").apply(pd.to_numeric, errors="coerce").sum(axis=1)
        emadm = d.filter(regex=r"^Emergency admissions via A&E").apply(pd.to_numeric, errors="coerce").sum(axis=1)
        dta = d.filter(regex=r"DTA to admission").apply(pd.to_numeric, errors="coerce").sum(axis=1)
        t = pd.DataFrame({"provider_code": d["Org Code"].astype(str).str.strip(),
                          "month": month, "ae_attendances": att,
                          "ae_over4hr": over4, "ae_emergency_adm": emadm, "ae_dta_delay": dta})
        rows.append(t)
    df = pd.concat(rows, ignore_index=True)
    df = df.groupby(["provider_code", "month"], as_index=False).sum()
    df = df[df["ae_attendances"] > 0]
    df["ae_4hr_breach_rate"] = df.ae_over4hr / df.ae_attendances
    df["emergency_admission_rate"] = df.ae_emergency_adm / df.ae_attendances
    df["ae_dta_delay_rate"] = df.ae_dta_delay / df.ae_attendances
    return df[["provider_code", "month", "ae_4hr_breach_rate",
               "emergency_admission_rate", "ae_dta_delay_rate"]]


# ---------------------------------------------------------------- diagnostics
def clean_diagnostics():
    rows = []
    for f in glob.glob(str(RAW / "diagnostics" / "**" / "*.xls"), recursive=True):
        name = Path(f).name
        if "Provider" not in name:
            continue
        y, m = period_from_text(name)
        month = f"{y}-{m:02d}" if (y and m) else None
        if month not in FY_MONTHS:
            continue
        d = pd.read_excel(f, sheet_name="Provider", header=13)
        d.columns = [str(c).strip() for c in d.columns]
        d = d.rename(columns={"Provider Code": "provider_code",
                              "Total Waiting List": "diag_total",
                              "Number waiting 6+ Weeks": "diag_6w"})
        d = d[d["provider_code"].notna()]
        d = d[~d["provider_code"].astype(str).str.lower().isin(["total", "nan"])]
        d["diag_total"] = pd.to_numeric(d["diag_total"], errors="coerce")
        d["diag_6w"] = pd.to_numeric(d["diag_6w"], errors="coerce")
        d = d[d["diag_total"] > 0]
        d["month"] = month
        d["diagnostic_over_6w_rate"] = d.diag_6w / d.diag_total
        rows.append(d[["provider_code", "month", "diagnostic_over_6w_rate"]])
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- beds KH03
def clean_beds():
    rows = []
    for f in glob.glob(str(RAW / "beds_kh03" / "**" / "*Open-Overnight*2025-26*.xlsx"), recursive=True):
        try:
            d = pd.read_excel(f, sheet_name="NHS Trust by Sector", header=14)
        except Exception:
            continue
        d.columns = [str(c).strip() for c in d.columns]
        # 3 'Total*' columns: Available, Occupied, % Occupied -> take 1st & 2nd
        totals = [i for i, c in enumerate(d.columns) if c.startswith("Total")]
        if len(totals) < 2:
            continue
        avail = d.iloc[:, totals[0]]
        occ = d.iloc[:, totals[1]]
        org = d["Org Code"].astype(str).str.strip() if "Org Code" in d.columns else None
        if org is None:
            continue
        q = None
        for cand in ("Q1", "Q2", "Q3", "Q4"):
            if cand.lower() in Path(f).name.lower():
                q = cand
        if not q:
            continue
        t = pd.DataFrame({"provider_code": org,
                          "available": pd.to_numeric(avail, errors="coerce"),
                          "occupied": pd.to_numeric(occ, errors="coerce")})
        t = t[(t.provider_code.str.len() == 3) & (t.available > 0)]
        t["bed_occupancy_rate"] = (t.occupied / t.available).clip(upper=1.2)
        for month in _months_in_quarter(q):
            tt = t.copy(); tt["month"] = month
            rows.append(tt[["provider_code", "month", "bed_occupancy_rate"]])
    return pd.concat(rows, ignore_index=True).groupby(
        ["provider_code", "month"], as_index=False).mean()


# ---------------------------------------------------------------- theatres
def clean_theatres():
    rows = []
    for f in glob.glob(str(RAW / "operating_theatres" / "**" / "*2025-26*.xlsx"), recursive=True):
        try:
            d = pd.read_excel(f, sheet_name="Operating Theatres", header=15)
        except Exception:
            continue
        d.columns = [str(c).strip() for c in d.columns]
        oc = [c for c in d.columns if "Organisation Code" in c]
        tot = [c for c in d.columns if c.startswith("Number of operating")]
        day = [c for c in d.columns if "dedicated" in c.lower() or "day case" in c.lower()]
        if not (oc and tot and day):
            continue
        q = next((c for c in ("Q1", "Q2", "Q3", "Q4") if c.lower() in Path(f).name.lower()), None)
        if not q:
            continue
        t = pd.DataFrame({"provider_code": d[oc[0]].astype(str).str.strip(),
                          "theatres": pd.to_numeric(d[tot[0]], errors="coerce"),
                          "daycase": pd.to_numeric(d[day[0]], errors="coerce")})
        t = t[(t.provider_code.str.len() == 3) & (t.theatres > 0)]
        t["theatre_daycase_share"] = (t.daycase / t.theatres).clip(0, 1)
        for month in _months_in_quarter(q):
            tt = t.copy(); tt["month"] = month
            rows.append(tt[["provider_code", "month", "theatre_daycase_share"]])
    return pd.concat(rows, ignore_index=True).groupby(
        ["provider_code", "month"], as_index=False).mean()


# ---------------------------------------------------------------- cancelled ops
def clean_cancelled():
    rows = []
    f = glob.glob(str(RAW / "cancelled_operations" / "QMCO-Annual*2025-26*.csv"))
    if f:
        d = pd.read_csv(f[0])
        d.columns = [c.strip() for c in d.columns]
        d = d.rename(columns={"Org Code": "provider_code",
                              "Cancelled Operations": "cancelled_operations",
                              "Breaches Of Standard": "cancel_28day_breaches",
                              "Period Name": "period_name"})
        d["provider_code"] = d["provider_code"].astype(str).str.strip()
        d = d[d.provider_code.str.len() == 3]
        qmap = {"JUNE": "Q1", "SEPTEMBER": "Q2", "DECEMBER": "Q3", "MARCH": "Q4"}
        for _, r in d.iterrows():
            q = qmap.get(str(r.get("period_name", "")).strip().upper())
            if not q:
                continue
            for month in _months_in_quarter(q):
                rows.append({"provider_code": r.provider_code, "month": month,
                             "cancelled_operations": pd.to_numeric(r.cancelled_operations, errors="coerce"),
                             "cancel_28day_breaches": pd.to_numeric(r.cancel_28day_breaches, errors="coerce")})
    out = pd.DataFrame(rows)
    return out.groupby(["provider_code", "month"], as_index=False).mean() if len(out) else out


SOURCES = {"ae": clean_ae, "diagnostics": clean_diagnostics, "beds": clean_beds,
           "theatres": clean_theatres, "cancelled": clean_cancelled}


def main():
    for name, fn in SOURCES.items():
        path = OUT / f"{name}.parquet"
        if path.exists():
            print(f"- {name}: cached ({len(pd.read_parquet(path))} rows)")
            continue
        print(f"- {name}: building…")
        df = fn()
        df.to_parquet(path, index=False)
        print(f"    {name}: {len(df)} rows, {df['provider_code'].nunique()} providers")

    # combine onto the full provider x month grid (FY 2025-26)
    parts = {n: pd.read_parquet(OUT / f"{n}.parquet") for n in SOURCES}
    base = pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")[
        ["provider_code", "month"]].drop_duplicates()
    op = base.copy()
    for n, df in parts.items():
        op = op.merge(df, on=["provider_code", "month"], how="left")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    op.to_parquet(PROCESSED / "operational_pressure.parquet", index=False)
    cov = {c: f"{100*op[c].notna().mean():.0f}%" for c in op.columns
           if c not in ("provider_code", "month")}
    print(f"\noperational_pressure.parquet: {len(op)} provider-months")
    print("coverage:", cov)


if __name__ == "__main__":
    main()
