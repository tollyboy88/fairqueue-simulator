"""Harmonise monthly full RTT extracts to provider x specialty x month.

The full CSVs contain commissioner-level rows. Counts are aggregated to
provider and treatment-function level before features are calculated.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import INTERIM, PROCESSED, RAW, financial_year, is_total_tfc, month_to_quarter, period_from_text  # noqa: E402

START = pd.Period("2022-04", freq="M")
END = pd.Period("2026-06", freq="M")
KEYS = ["provider_code", "treatment_function_code"]
PART_MAP = {
    "Part_2": "incomplete_total",
    "Part_2A": "dta_total",
    "Part_3": "new_rtt_total",
    "Part_1A": "admitted_total",
    "Part_1B": "non_admitted_total",
}


def month_from_text(text: str) -> pd.Period | None:
    year, month = period_from_text(text)
    return pd.Period(f"{year}-{month:02d}", freq="M") if year and month else None


def archives() -> dict[pd.Period, Path]:
    candidates: dict[pd.Period, list[Path]] = {}
    for root in (RAW / "rtt", RAW / "rtt_longitudinal"):
        if not root.exists():
            continue
        for path in root.rglob("*.zip"):
            low = path.name.lower()
            if "full-csv" not in low and not low.startswith("rtt_"):
                continue
            month = month_from_text(path.name)
            if month and START <= month <= END:
                candidates.setdefault(month, []).append(path)
    # Prefer canonical downloads, then revised releases.
    return {
        month: sorted(
            paths,
            key=lambda path: (
                path.parent.name != "rtt_longitudinal",
                "revised" not in path.name.lower(),
                len(str(path)),
            ),
        )[0]
        for month, paths in candidates.items()
    }


def csv_member(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    if not members:
        raise ValueError(f"No CSV member in {path}")
    return max(members, key=len)


def parse_archive(path: Path, month: pd.Period) -> pd.DataFrame:
    member = csv_member(path)
    with zipfile.ZipFile(path) as archive, archive.open(member) as stream:
        header = pd.read_csv(stream, nrows=0).columns.tolist()

    identifiers = [
        "Provider Org Code",
        "Provider Org Name",
        "RTT Part Type",
        "Treatment Function Code",
        "Treatment Function Name",
        "Total All",
    ]
    band_columns = [column for column in header if re.match(r"Gt \d{2,3}(?: To \d{2,3})? Weeks SUM 1", column)]
    within_columns = [
        column for column in band_columns
        if int(re.search(r"Gt (\d{2,3})", column).group(1)) < 18
    ]
    over52_columns = [
        column for column in band_columns
        if int(re.search(r"Gt (\d{2,3})", column).group(1)) >= 52
    ]
    usecols = [column for column in identifiers + within_columns + over52_columns if column in header]
    required = {"Provider Org Code", "RTT Part Type", "Treatment Function Code", "Total All"}
    if not required.issubset(usecols):
        raise ValueError(f"Unexpected RTT schema in {path.name}; missing {sorted(required - set(usecols))}")

    partial = []
    with zipfile.ZipFile(path) as archive, archive.open(member) as stream:
        for chunk in pd.read_csv(stream, usecols=usecols, chunksize=40_000, low_memory=False):
            chunk = chunk[chunk["Provider Org Code"].notna()].copy()
            chunk = chunk[
                ~chunk.apply(
                    lambda row: is_total_tfc(
                        row["Treatment Function Code"], row.get("Treatment Function Name")
                    ),
                    axis=1,
                )
            ]
            chunk = chunk[chunk["RTT Part Type"].isin(PART_MAP)]
            numeric = ["Total All"] + within_columns + over52_columns
            for column in numeric:
                if column in chunk:
                    chunk[column] = pd.to_numeric(chunk[column], errors="coerce").fillna(0)
            chunk["within_18w"] = chunk[[c for c in within_columns if c in chunk]].sum(axis=1)
            chunk["breach_52w_count"] = chunk[[c for c in over52_columns if c in chunk]].sum(axis=1)
            partial.append(
                chunk.groupby(
                    [
                        "Provider Org Code",
                        "Provider Org Name",
                        "Treatment Function Code",
                        "Treatment Function Name",
                        "RTT Part Type",
                    ],
                    as_index=False,
                    dropna=False,
                )[["Total All", "within_18w", "breach_52w_count"]].sum()
            )

    data = pd.concat(partial, ignore_index=True)
    data = data.groupby(
        [
            "Provider Org Code",
            "Provider Org Name",
            "Treatment Function Code",
            "Treatment Function Name",
            "RTT Part Type",
        ],
        as_index=False,
        dropna=False,
    )[["Total All", "within_18w", "breach_52w_count"]].sum()

    base = data[data["RTT Part Type"] == "Part_2"].copy()
    base = base.rename(
        columns={
            "Provider Org Code": "provider_code",
            "Provider Org Name": "provider_name",
            "Treatment Function Code": "treatment_function_code",
            "Treatment Function Name": "treatment_function_name",
            "Total All": "incomplete_total",
        }
    )
    base["breach_18w_count"] = (base["incomplete_total"] - base["within_18w"]).clip(lower=0)
    base = base.drop(columns="within_18w")
    for part, column in PART_MAP.items():
        if part == "Part_2":
            continue
        addition = data[data["RTT Part Type"] == part][
            ["Provider Org Code", "Treatment Function Code", "Total All"]
        ].rename(
            columns={
                "Provider Org Code": "provider_code",
                "Treatment Function Code": "treatment_function_code",
                "Total All": column,
            }
        )
        base = base.merge(addition, on=KEYS, how="left")

    for column in PART_MAP.values():
        base[column] = pd.to_numeric(base.get(column), errors="coerce").fillna(0)
    base["breach_52w_count"] = pd.to_numeric(base["breach_52w_count"], errors="coerce").fillna(0)
    base["month"] = str(month)
    base["quarter"] = f"{month_to_quarter(month.month)} {financial_year(month.year, month.month)}"
    base["financial_year"] = financial_year(month.year, month.month)
    base["region_code"] = np.nan
    return base[
        [
            "month",
            "quarter",
            "financial_year",
            "region_code",
            "provider_code",
            "provider_name",
            "treatment_function_code",
            "treatment_function_name",
            "incomplete_total",
            "breach_18w_count",
            "breach_52w_count",
            "dta_total",
            "new_rtt_total",
            "admitted_total",
            "non_admitted_total",
        ]
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    found = archives()
    expected = set(pd.period_range(START, END, freq="M"))
    if set(found) != expected:
        missing = sorted(str(month) for month in expected - set(found))
        raise RuntimeError(
            "RTT coverage incomplete; run 01_download_longitudinal_data.py. "
            f"Missing: {missing}"
        )

    cache = INTERIM / "rtt_v2" / "by_month"
    cache.mkdir(parents=True, exist_ok=True)
    frames = []
    for month in sorted(found):
        cached = cache / f"rtt_{month}.parquet"
        if args.force or not cached.exists():
            print(f"clean RTT {month}: {found[month].name}")
            parse_archive(found[month], month).to_parquet(cached, index=False)
        else:
            print(f"reuse RTT {month}: {cached.name}")
        frames.append(pd.read_parquet(cached))

    result = pd.concat(frames, ignore_index=True)
    result = result.drop_duplicates(["month", *KEYS]).sort_values(["month", *KEYS])
    out_interim = INTERIM / "rtt_v2" / "rtt_provider_specialty_month.parquet"
    out_processed = PROCESSED / "rtt_provider_specialty_month.parquet"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out_interim, index=False)
    result.to_parquet(out_processed, index=False)
    print(
        f"Wrote {len(result):,} rows; months={result.month.nunique()}, "
        f"providers={result.provider_code.nunique()}, "
        f"specialties={result.treatment_function_code.nunique()}"
    )


if __name__ == "__main__":
    main()
