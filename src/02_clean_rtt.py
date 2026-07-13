"""
02_clean_rtt.py
---------------
Build the RTT provider x specialty x month table from the 12 monthly
NHS England RTT releases.

Outputs:
    data/interim/rtt_cleaned/rtt_provider_specialty_month.parquet
    data/processed/rtt_provider_specialty_month.parquet   (copy for modelling)

Columns produced:
    month, quarter, financial_year, region_code,
    provider_code, provider_name,
    treatment_function_code, treatment_function_name,
    incomplete_total, total_within_18w, breach_18w_count, breach_52w_count,
    dta_total, new_rtt_total, admitted_total, non_admitted_total
"""
from pathlib import Path
import glob
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import (RAW, INTERIM, PROCESSED, period_from_text,
                   month_to_quarter, financial_year, is_total_tfc)  # noqa

RTT_DIR = RAW / "rtt" / "RTT REFERAL 2025-2026"

KEYS = ["provider_code", "treatment_function_code"]
RENAME_KEYS = {
    "Region Code": "region_code",
    "Provider Code": "provider_code",
    "Provider Name": "provider_name",
    "Treatment Function Code": "treatment_function_code",
    "Treatment Function": "treatment_function_name",
}


def _read(path, sheet, value_cols: dict):
    """Read an RTT provider sheet (header on row 14) and keep key + value cols."""
    df = pd.read_excel(path, sheet_name=sheet, header=13, engine="openpyxl")
    df = df.rename(columns={**RENAME_KEYS, **value_cols})
    keep = ["region_code", "provider_code", "provider_name",
            "treatment_function_code", "treatment_function_name"] + list(value_cols.values())
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()
    # drop rows without a provider code and aggregate "Total" specialty rows
    df = df[df["provider_code"].notna()]
    df = df[~df.apply(lambda r: is_total_tfc(r["treatment_function_code"],
                                             r.get("treatment_function_name")), axis=1)]
    for v in value_cols.values():
        if v in df.columns:
            df[v] = pd.to_numeric(df[v], errors="coerce")
    return df


def _first(patt, folder):
    hits = glob.glob(str(folder / patt))
    return hits[0] if hits else None


def process_month(folder: Path):
    year, month = period_from_text(folder.name)
    if not (year and month):
        print(f"  ! could not parse period from {folder.name}; skipping")
        return None
    month_str = f"{year}-{month:02d}"

    inc_path = _first("Incomplete-Provider*", folder)
    adm_path = _first("Admitted-Provider*", folder)
    nadm_path = _first("NonAdmitted-Provider*", folder)
    new_path = _first("New-Periods-Provider*", folder)
    if not inc_path:
        print(f"  ! no Incomplete-Provider file in {folder.name}; skipping")
        return None

    inc = _read(inc_path, "Provider", {
        "Total number of incomplete pathways": "incomplete_total",
        "Total within 18 weeks": "total_within_18w",
        "Total 52 plus weeks": "breach_52w_count",
    })
    dta = _read(inc_path, "Provider with DTA", {
        "Total number of incomplete pathways with a decision to admit for treatment": "dta_total",
    })[KEYS + ["dta_total"]]

    df = inc.merge(dta, on=KEYS, how="left")

    if adm_path:
        adm = _read(adm_path, "Provider",
                    {"Total number of completed pathways (all)": "admitted_total"})[KEYS + ["admitted_total"]]
        df = df.merge(adm, on=KEYS, how="left")
    if nadm_path:
        nadm = _read(nadm_path, "Provider",
                     {"Total number of completed pathways (all)": "non_admitted_total"})[KEYS + ["non_admitted_total"]]
        df = df.merge(nadm, on=KEYS, how="left")
    if new_path:
        new = _read(new_path, "Provider",
                    {"Number of new RTT clock starts during the month": "new_rtt_total"})[KEYS + ["new_rtt_total"]]
        df = df.merge(new, on=KEYS, how="left")

    df["breach_18w_count"] = (df["incomplete_total"] - df["total_within_18w"]).clip(lower=0)
    df.insert(0, "month", month_str)
    df.insert(1, "quarter", f"{month_to_quarter(month)} {financial_year(year, month)}")
    df.insert(2, "financial_year", financial_year(year, month))
    return df


def main():
    cache = INTERIM / "rtt_cleaned" / "by_month"
    cache.mkdir(parents=True, exist_ok=True)
    folders = sorted([p for p in RTT_DIR.iterdir() if p.is_dir()])
    print(f"Found {len(folders)} RTT month folders")
    for folder in folders:
        year, month = period_from_text(folder.name)
        tag = f"{year}-{month:02d}" if (year and month) else folder.name
        cache_path = cache / f"rtt_{tag}.parquet"
        if cache_path.exists():
            print(f"- {folder.name}  (cached)")
            continue
        print(f"- {folder.name}")
        out = process_month(folder)
        if out is not None:
            out.to_parquet(cache_path, index=False)
            print(f"    rows={len(out)} providers={out['provider_code'].nunique()} "
                  f"specialties={out['treatment_function_code'].nunique()} -> cached")

    cached = sorted(cache.glob("rtt_*.parquet"))
    print(f"\nCombining {len(cached)}/{len(folders)} cached months")
    if len(cached) < len(folders):
        print("Not all months processed yet — re-run to continue.")
        return None
    frames = [pd.read_parquet(p) for p in cached]
    full = pd.concat(frames, ignore_index=True)
    for c in ["incomplete_total", "breach_18w_count", "breach_52w_count",
              "dta_total", "new_rtt_total", "admitted_total", "non_admitted_total"]:
        if c in full.columns:
            full[c] = full[c].fillna(0)

    INTERIM.joinpath("rtt_cleaned").mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    o1 = INTERIM / "rtt_cleaned" / "rtt_provider_specialty_month.parquet"
    o2 = PROCESSED / "rtt_provider_specialty_month.parquet"
    full.to_parquet(o1, index=False)
    full.to_parquet(o2, index=False)
    print(f"\nWrote {len(full):,} rows x {full.shape[1]} cols")
    print(f"  {o1}\n  {o2}")
    print("Months:", sorted(full['month'].unique()))
    return full


if __name__ == "__main__":
    main()
