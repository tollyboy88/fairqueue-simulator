"""Build separate provider-level disparity indicators from WLMDS geography data.

Demographic indicators are never used by the forecasting model. They are
retained separately for the later equity-constrained decision layer.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import INTERIM, PROCESSED, RAW  # noqa: E402

LONG_BAND = "Over 52 Weeks"
ALL_BAND = "Total"
SNAPSHOT_RELEASES = {
    pd.Timestamp("2026-02-22"): {
        "available_date": pd.Timestamp("2026-03-12"),
        "filename": "WLMDS-Demographics-Geography-to-22-February-2026-v1.csv",
    },
    pd.Timestamp("2026-03-29"): {
        "available_date": pd.Timestamp("2026-05-14"),
        "filename": "WLMDS-Demographics-Geography-to-29-March-2026-v2.csv",
    },
    pd.Timestamp("2026-04-26"): {
        "available_date": pd.Timestamp("2026-06-11"),
        "filename": "WLMDS-Demographics-Geography-to-26-April-2026-v1.csv",
    },
}


def dated_geography_files() -> list[tuple[pd.Timestamp, Path]]:
    files = []
    for path in (RAW / "wlmds").rglob("*Demographics-Geography*.csv"):
        match = re.search(r"to-(\d{1,2})-([A-Za-z]+)-(20\d{2})", path.name)
        if match:
            files.append((pd.to_datetime(" ".join(match.groups()), dayfirst=True), path))
    return sorted(files)


def gaps(group: pd.DataFrame) -> pd.DataFrame:
    all_waits = group[group["Waiting Bands"] == ALL_BAND].groupby("Category")["Count"].sum()
    long_waits = group[group["Waiting Bands"] == LONG_BAND].groupby("Category")["Count"].sum()
    categories = sorted(set(all_waits.index) | set(long_waits.index))
    all_waits = all_waits.reindex(categories).fillna(0)
    long_waits = long_waits.reindex(categories).fillna(0)
    if all_waits.sum() <= 0 or long_waits.sum() <= 0:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "category": categories,
            "share_all": (all_waits / all_waits.sum()).values,
            "share_long": (long_waits / long_waits.sum()).values,
        }
    ).assign(disparity=lambda frame: frame.share_long - frame.share_all)


def main() -> None:
    available = dated_geography_files()
    if not available:
        raise FileNotFoundError("No WLMDS Demographics Geography CSV found under data/raw/wlmds")
    summaries, details = [], []
    used_files = []
    for snapshot_date, path in available:
        release = SNAPSHOT_RELEASES.get(snapshot_date)
        if release is None or path.name != release["filename"]:
            continue
        available_date = release["available_date"]
        raw = pd.read_csv(path)
        raw["Count"] = pd.to_numeric(raw["Count"], errors="coerce").fillna(0)
        provider = raw[raw["Geography"].isin(["NHS ACUTE", "INDEPENDENT SECTOR", "OTHER"])].copy()
        for code, provider_rows in provider.groupby("Code"):
            record = {
                "provider_code": str(code).strip(),
                "provider_name": provider_rows["Name"].iloc[0],
                "snapshot_date": snapshot_date,
                "available_date": available_date,
            }
            for metric, key in (
                ("IMD", "deprivation_disparity"),
                ("Ethnicity", "ethnicity_disparity"),
                ("Age", "age_disparity"),
                ("Sex", "sex_disparity"),
            ):
                table = gaps(provider_rows[provider_rows["Metric"] == metric])
                if table.empty:
                    record[key] = float("nan")
                    continue
                table.insert(0, "metric", metric)
                table.insert(0, "provider_code", str(code).strip())
                table.insert(0, "available_date", available_date)
                table.insert(0, "snapshot_date", snapshot_date)
                details.append(table)
                record[key] = float(
                    table.disparity.abs().max()
                    if metric == "Sex"
                    else table.disparity.clip(lower=0).max()
                )
            ethnicity_total = provider_rows[
                (provider_rows["Metric"] == "Ethnicity")
                & (provider_rows["Waiting Bands"] == ALL_BAND)
            ]
            denominator = ethnicity_total["Count"].sum()
            unknown = ethnicity_total[
                ethnicity_total["Category"].astype(str).str.contains(
                    "not known|unknown", case=False, regex=True
                )
            ]["Count"].sum()
            record["missing_demographic_share"] = (
                float(unknown / denominator) if denominator else float("nan")
            )
            summaries.append(record)
        used_files.append(path.name)

    if not summaries:
        raise RuntimeError(
            "No WLMDS geography file has a declared publication-availability date"
        )

    summary = pd.DataFrame(summaries)
    detail = pd.concat(details, ignore_index=True)
    folder = INTERIM / "wlmds_v2"
    folder.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    summary.to_parquet(folder / "provider_disparities.parquet", index=False)
    detail.to_parquet(folder / "provider_disparities_detail.parquet", index=False)
    summary.to_parquet(PROCESSED / "provider_disparities.parquet", index=False)
    print(
        f"Wrote {len(summary)} provider disparity rows from {len(used_files)} snapshots: "
        f"{', '.join(used_files)}"
    )


if __name__ == "__main__":
    main()
