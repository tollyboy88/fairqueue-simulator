"""
01_extract_data.py
------------------
Walk data/raw/ and build a catalogue of every source file:
file_name, folder (category), data_source, period, file_type, status, notes.
Writes outputs/data_catalogue.csv.
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import RAW, OUTPUTS, period_from_text, month_to_quarter, financial_year  # noqa

CATEGORY_SOURCE = {
    "rtt": "RTT referral-to-treatment (NHS England)",
    "wlmds": "Waiting List Minimum Data Set (demographics/fairness)",
    "ons_population": "ONS mid-year population estimates",
    "ons_ethnicity": "ONS / Census ethnicity",
    "imd": "Index of Multiple Deprivation 2019",
    "diagnostics": "Monthly Diagnostics waiting times (DM01)",
    "ae_emergency": "A&E attendances & emergency admissions",
    "beds_kh03": "Bed availability & occupancy (KH03)",
    "uec_sitrep": "Urgent & Emergency Care daily situation report",
    "operating_theatres": "Operating theatres quarterly",
    "cancelled_operations": "Cancelled elective operations (QMCO)",
}


def main():
    rows = []
    for cat_dir in sorted(RAW.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name
        for f in sorted(cat_dir.rglob("*")):
            if f.is_dir():
                continue
            rel = f.relative_to(RAW)
            # period inference from file then parent folder
            year, month = period_from_text(f.name)
            if year is None:
                year, month = period_from_text(f.parent.name)
            if year and month:
                period = f"{year}-{month:02d}"
                qtr = f"{month_to_quarter(month)} {financial_year(year, month)}"
            elif year:
                period = str(year)
                qtr = ""
            else:
                period, qtr = "", ""
            rows.append({
                "file_name": f.name,
                "folder": cat,
                "sub_path": str(rel.parent) if str(rel.parent) != cat else "",
                "data_source": CATEGORY_SOURCE.get(cat, cat),
                "period": period,
                "quarter": qtr,
                "file_type": f.suffix.lower().lstrip("."),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "status": "raw",
                "notes": "",
            })
    df = pd.DataFrame(rows).sort_values(["folder", "period", "file_name"])
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    out = OUTPUTS / "data_catalogue.csv"
    df.to_csv(out, index=False)
    print(f"Catalogued {len(df)} files -> {out}")
    print(df.groupby('folder').agg(files=('file_name', 'size'),
                                   size_mb=('size_kb', lambda s: round(s.sum()/1024, 1))))


if __name__ == "__main__":
    main()
