"""Create availability-aware provider-level operational predictors.

Monthly diagnostics are shifted one month. Quarterly bed and cancellation
statistics are assigned only to the following quarter. This conservative lag
prevents publication-timing leakage.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import INTERIM, PROCESSED, RAW, period_from_text  # noqa: E402

START = pd.Period("2022-04", freq="M")
END = pd.Period("2026-06", freq="M")


def dated_archives(root: Path, marker: str) -> dict[pd.Period, Path]:
    candidates: dict[pd.Period, list[Path]] = {}
    for path in root.rglob("*.zip"):
        low = path.name.lower()
        canonical = path.parent.name == "dm01_longitudinal" and low.startswith("dm01_")
        if (marker not in low and not canonical) or "cdc" in low:
            continue
        year, month = period_from_text(path.name)
        if year and month:
            period = pd.Period(f"{year}-{month:02d}", freq="M")
            if START <= period <= END:
                candidates.setdefault(period, []).append(path)
    return {
        month: sorted(paths, key=lambda path: (path.parent.name != "dm01_longitudinal", len(str(path))))[0]
        for month, paths in candidates.items()
    }


def clean_diagnostics() -> pd.DataFrame:
    rows = []
    archives = dated_archives(RAW, "full-extract")
    for source_month, path in sorted(archives.items()):
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                continue
            with archive.open(max(members, key=len)) as stream:
                header = pd.read_csv(stream, nrows=0).columns.tolist()
            provider_col = next(
                (column for column in ("Provider Org Code", "Provider Code") if column in header),
                None,
            )
            total_col = next((column for column in ("Total WL", "Total Waiting List") if column in header), None)
            wait_columns = [
                column
                for column in header
                if re.match(r"(?:0?6|0?[7-9]|1[0-3])\s*<|13\+", str(column))
            ]
            if not provider_col or not total_col or not wait_columns:
                raise ValueError(f"Unexpected DM01 schema in {path.name}")
            usecols = [provider_col, total_col, *wait_columns]
            with archive.open(max(members, key=len)) as stream:
                data = pd.read_csv(stream, usecols=usecols, low_memory=False)
        for column in [total_col, *wait_columns]:
            data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0)
        grouped = data.groupby(provider_col, as_index=False)[[total_col, *wait_columns]].sum()
        grouped["diagnostic_over_6w_rate"] = (
            grouped[wait_columns].sum(axis=1) / grouped[total_col].replace(0, np.nan)
        )
        grouped = grouped.rename(columns={provider_col: "provider_code"})
        # Month t is conservatively considered usable from t+1.
        available_month = source_month + 1
        if available_month <= END:
            grouped["month"] = str(available_month)
            rows.append(grouped[["provider_code", "month", "diagnostic_over_6w_rate"]])
    return pd.concat(rows, ignore_index=True)


def expand_completed_quarter(frame: pd.DataFrame, date_column: str) -> pd.DataFrame:
    expanded = []
    for _, row in frame.iterrows():
        period = pd.Timestamp(row[date_column]).to_period("M")
        for offset in (1, 2, 3):
            month = period + offset
            if START <= month <= END:
                copy = row.copy()
                copy["month"] = str(month)
                expanded.append(copy)
    return pd.DataFrame(expanded).drop(columns=date_column)


def clean_beds() -> pd.DataFrame:
    available_path = next((RAW / "beds_kh03").rglob("KH03-Available-Overnight-only.csv"))
    occupied_path = next((RAW / "beds_kh03").rglob("KH03-Occupied-Overnight-only.csv"))
    available = pd.read_csv(available_path)
    occupied = pd.read_csv(occupied_path)
    keys = ["Organisation_Code", "Effective_Snapshot_Date"]
    available["Number_Of_Beds"] = pd.to_numeric(available["Number_Of_Beds"], errors="coerce")
    occupied["Number_Of_Beds"] = pd.to_numeric(occupied["Number_Of_Beds"], errors="coerce")
    available = available.groupby(keys, as_index=False)["Number_Of_Beds"].sum().rename(
        columns={"Number_Of_Beds": "available_beds"}
    )
    occupied = occupied.groupby(keys, as_index=False)["Number_Of_Beds"].sum().rename(
        columns={"Number_Of_Beds": "occupied_beds"}
    )
    data = available.merge(occupied, on=keys, how="inner")
    data["Effective_Snapshot_Date"] = pd.to_datetime(
        data["Effective_Snapshot_Date"], dayfirst=True
    )
    data["bed_occupancy_rate"] = (
        data["occupied_beds"] / data["available_beds"].replace(0, np.nan)
    ).clip(0, 1.2)
    data = data.rename(columns={"Organisation_Code": "provider_code"})
    historical = expand_completed_quarter(
        data[["provider_code", "Effective_Snapshot_Date", "bed_occupancy_rate"]],
        "Effective_Snapshot_Date",
    )
    workbook_rows = []
    for path in (RAW / "beds_kh03").rglob("*Open-Overnight*20*.xlsx"):
        match = re.search(r"Q([1-4])-(20\d{2})-(\d{2})", path.name, flags=re.I)
        if not match:
            continue
        quarter, start_year = int(match.group(1)), int(match.group(2))
        try:
            excel = pd.ExcelFile(path)
            sheet = next(name for name in excel.sheet_names if "NHS Trust by Sector" in name)
            preview = pd.read_excel(path, sheet_name=sheet, header=None, nrows=25)
            header_row = next(
                index
                for index, row in preview.iterrows()
                if row.astype(str).str.strip().eq("Org Code").any()
            )
            quarter_data = pd.read_excel(path, sheet_name=sheet, header=header_row)
        except (ValueError, StopIteration):
            continue
        quarter_data.columns = [str(column).strip() for column in quarter_data.columns]
        if "Org Code" not in quarter_data.columns:
            continue
        total_columns = [column for column in quarter_data.columns if column.startswith("Total")]
        if len(total_columns) < 2:
            continue
        available_values = pd.to_numeric(quarter_data[total_columns[0]], errors="coerce")
        occupied_values = pd.to_numeric(quarter_data[total_columns[1]], errors="coerce")
        parsed = pd.DataFrame(
            {
                "provider_code": quarter_data["Org Code"].astype(str).str.strip(),
                "bed_occupancy_rate": (occupied_values / available_values.replace(0, np.nan)).clip(0, 1.2),
            }
        )
        end_month = {1: 6, 2: 9, 3: 12, 4: 3}[quarter]
        end_year = start_year + 1 if quarter == 4 else start_year
        parsed["Effective_Snapshot_Date"] = pd.Timestamp(end_year, end_month, 1) + pd.offsets.MonthEnd(0)
        workbook_rows.append(parsed.dropna(subset=["bed_occupancy_rate"]))
    if workbook_rows:
        recent = expand_completed_quarter(
            pd.concat(workbook_rows, ignore_index=True),
            "Effective_Snapshot_Date",
        )
        historical = pd.concat([historical, recent], ignore_index=True)
        historical = (
            historical.sort_values(["provider_code", "month"])
            .drop_duplicates(["provider_code", "month"], keep="last")
        )
    return historical


def read_cancelled(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name=0)


def clean_cancellations() -> pd.DataFrame:
    files = list(
        {
            path.name: path
            for path in (RAW / "cancelled_operations").rglob("QMCO-Annual-CSV-Q4-*")
            if path.suffix.lower() in {".csv", ".xlsx"}
        }.values()
    )
    frames = []
    for path in files:
        data = read_cancelled(path)
        if not {"Year", "Period Name", "Org Code", "Cancelled Operations"}.issubset(data.columns):
            continue
        data = data.rename(
            columns={
                "Org Code": "provider_code",
                "Cancelled Operations": "cancelled_operations",
                "Breaches Of Standard": "cancel_28day_breaches",
            }
        )
        data["cancelled_operations"] = pd.to_numeric(
            data["cancelled_operations"], errors="coerce"
        )
        data["cancel_28day_breaches"] = pd.to_numeric(
            data.get("cancel_28day_breaches"), errors="coerce"
        )
        month_number = data["Period Name"].astype(str).str.upper().map(
            {"JUNE": 6, "SEPTEMBER": 9, "DECEMBER": 12, "MARCH": 3}
        )
        start_year = pd.to_numeric(
            data["Year"].astype(str).str.extract(r"(20\d{2})")[0], errors="coerce"
        )
        calendar_year = np.where(month_number.eq(3), start_year + 1, start_year)
        data["quarter_end"] = pd.to_datetime(
            {
                "year": calendar_year,
                "month": month_number,
                "day": 1,
            },
            errors="coerce",
        ) + pd.offsets.MonthEnd(0)
        frames.append(
            data[
                [
                    "provider_code",
                    "quarter_end",
                    "cancelled_operations",
                    "cancel_28day_breaches",
                ]
            ]
        )
    combined = pd.concat(frames, ignore_index=True).dropna(subset=["quarter_end"])
    combined = combined.groupby(["provider_code", "quarter_end"], as_index=False)[
        ["cancelled_operations", "cancel_28day_breaches"]
    ].sum()
    return expand_completed_quarter(combined, "quarter_end")


def main() -> None:
    diagnostics = clean_diagnostics()
    beds = clean_beds()
    cancellations = clean_cancellations()
    result = diagnostics.merge(beds, on=["provider_code", "month"], how="outer")
    result = result.merge(cancellations, on=["provider_code", "month"], how="outer")
    result["provider_code"] = result["provider_code"].astype(str).str.strip()
    result = result.sort_values(["month", "provider_code"])
    folder = INTERIM / "operational_v2"
    folder.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    result.to_parquet(folder / "operational_pressure.parquet", index=False)
    result.to_parquet(PROCESSED / "operational_pressure.parquet", index=False)
    print(
        f"Wrote {len(result):,} provider-month operational rows; "
        f"months={result.month.nunique()}"
    )
    print(result.notna().mean().round(3).to_string())


if __name__ == "__main__":
    main()
