"""
00_arrange_raw_data.py
----------------------
Extract every file from Data.zip and place it into the blueprint's
data/raw/<category>/ structure. Resumable: skips files already extracted.

Usage:
    python src/00_arrange_raw_data.py [category]
If a category is given, only that category is extracted (useful to stay
inside short time limits). Otherwise all categories are processed.
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "Data.zip"
RAW = ROOT / "data" / "raw"


def categorise(segment: str) -> str:
    """Map the first path segment under Data/ to a raw category."""
    s = segment
    low = s.lower()
    if s == "RTT REFERAL 2025-2026":
        return "rtt"
    if s == "WLMDS":
        return "wlmds"
    if "monthly-diagnostics" in low:
        return "diagnostics"
    if "operating-theatres" in low:
        return "operating_theatres"
    if "ancelled" in low or s.startswith("QMCO"):
        return "cancelled_operations"
    if s == "A&E attendances and emergency admissions":
        return "ae_emergency"
    if "bed availability and occupancy" in low:
        return "beds_kh03"
    if "urgent and emergency care daily situation" in low:
        return "uec_sitrep"
    if s.startswith("File_1_-_IMD2019") or s.startswith("File_2_-_IoD2019"):
        return "imd"
    if "ethnic" in low:
        return "ons_ethnicity"
    if ("population" in low) or s.startswith("Figure_1__Revisions"):
        return "ons_population"
    return "UNMATCHED"


def main(only: str | None = None):
    z = zipfile.ZipFile(ZIP_PATH)
    placed, skipped, unmatched = 0, 0, []
    for info in z.infolist():
        name = info.filename
        if name.endswith("/"):
            continue
        parts = name.split("/")
        if parts[0] != "Data" or len(parts) < 2:
            continue
        segment = parts[1]
        cat = categorise(segment)
        if cat == "UNMATCHED":
            unmatched.append(name)
            continue
        if only and cat != only:
            continue
        # destination keeps the structure below the top Data/ segment
        rel = "/".join(parts[1:])
        dest = RAW / cat / rel
        if dest.exists() and dest.stat().st_size == info.file_size:
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as src, open(dest, "wb") as out:
            out.write(src.read())
        placed += 1
    print(f"[{only or 'ALL'}] placed={placed} skipped={skipped} unmatched={len(unmatched)}")
    if unmatched:
        print("UNMATCHED (first 20):")
        for u in unmatched[:20]:
            print("  ", u)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
