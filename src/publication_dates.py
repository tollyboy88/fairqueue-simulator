"""Official NHS England publication dates used for as-of feature construction.

Dates were transcribed from NHS England's published 12-month statistics calendars.
Keys for monthly series are reporting months; keys for quarterly series are quarter-end
months.  The dictionaries intentionally record first publication dates, not later
revision dates.
"""
from __future__ import annotations

import pandas as pd


CALENDAR_SOURCE_URLS = (
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2022/09/"
    "20220923-Proposed-12-month-plan-for-2022-23.pdf",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2023/09/"
    "20230918-Proposed-12-month-plan-for-2023-24.pdf",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/05/"
    "20240510-Proposed-12-month-plan-for-2024-25.pdf",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/03/"
    "20250307-Proposed-12-month-plan-for-2025-26.pdf",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/12/"
    "20251217-Proposed-12-month-plan-for-2025-26.pdf",
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/04/"
    "Proposed-12-month-plan-for-2026-27-for-publication-3.pdf",
)


def _monthly(values: dict[str, str]) -> dict[pd.Period, pd.Timestamp]:
    return {
        pd.Period(month, freq="M"): pd.Timestamp(date)
        for month, date in values.items()
    }


RTT_PUBLICATION_DATES = _monthly(
    {
        "2022-04": "2022-06-16",
        "2022-05": "2022-07-14",
        "2022-06": "2022-08-11",
        "2022-07": "2022-09-08",
        "2022-08": "2022-10-13",
        "2022-09": "2022-11-10",
        "2022-10": "2022-12-08",
        "2022-11": "2023-01-12",
        "2022-12": "2023-02-09",
        "2023-01": "2023-03-09",
        "2023-02": "2023-04-13",
        "2023-03": "2023-05-11",
        "2023-04": "2023-06-08",
        "2023-05": "2023-07-13",
        "2023-06": "2023-08-10",
        "2023-07": "2023-09-14",
        "2023-08": "2023-10-12",
        "2023-09": "2023-11-09",
        "2023-10": "2023-12-14",
        "2023-11": "2024-01-11",
        "2023-12": "2024-02-08",
        "2024-01": "2024-03-14",
        "2024-02": "2024-04-11",
        "2024-03": "2024-05-09",
        "2024-04": "2024-06-13",
        "2024-05": "2024-07-11",
        "2024-06": "2024-08-08",
        "2024-07": "2024-09-12",
        "2024-08": "2024-10-10",
        "2024-09": "2024-11-14",
        "2024-10": "2024-12-12",
        "2024-11": "2025-01-09",
        "2024-12": "2025-02-13",
        "2025-01": "2025-03-13",
        "2025-02": "2025-04-10",
        "2025-03": "2025-05-15",
        "2025-04": "2025-06-12",
        "2025-05": "2025-07-10",
        "2025-06": "2025-08-14",
        "2025-07": "2025-09-11",
        "2025-08": "2025-10-09",
        "2025-09": "2025-11-13",
        "2025-10": "2025-12-11",
        "2025-11": "2026-01-15",
        "2025-12": "2026-02-12",
        "2026-01": "2026-03-12",
        "2026-02": "2026-04-16",
        "2026-03": "2026-05-14",
        "2026-04": "2026-06-11",
        "2026-05": "2026-07-09",
        "2026-06": "2026-08-13",
    }
)

# Monthly diagnostics are released on the same NHS England statistics date as RTT.
DIAGNOSTIC_PUBLICATION_DATES = RTT_PUBLICATION_DATES.copy()

BED_PUBLICATION_DATES = _monthly(
    {
        "2022-03": "2022-05-19",
        "2022-06": "2022-08-18",
        "2022-09": "2022-11-17",
        "2022-12": "2023-02-23",
        "2023-03": "2023-05-25",
        "2023-06": "2023-08-24",
        "2023-09": "2023-11-23",
        "2023-12": "2024-02-22",
        "2024-03": "2024-05-23",
        "2024-06": "2024-08-22",
        "2024-09": "2024-11-21",
        "2024-12": "2025-02-20",
        "2025-03": "2025-05-22",
        "2025-06": "2025-08-21",
        "2025-09": "2025-11-20",
        "2025-12": "2026-02-19",
        "2026-03": "2026-05-22",
    }
)

CANCELLATION_PUBLICATION_DATES = _monthly(
    {
        "2022-03": "2022-05-12",
        "2022-06": "2022-08-11",
        "2022-09": "2022-11-10",
        "2022-12": "2023-02-09",
        "2023-03": "2023-05-11",
        "2023-06": "2023-08-10",
        "2023-09": "2023-11-09",
        "2023-12": "2024-02-08",
        "2024-03": "2024-05-09",
        "2024-06": "2024-08-08",
        "2024-09": "2024-11-14",
        "2024-12": "2025-02-13",
        "2025-03": "2025-05-15",
        "2025-06": "2025-08-14",
        "2025-09": "2025-11-13",
        "2025-12": "2026-02-12",
        "2026-03": "2026-05-14",
    }
)


def dates_for_months(
    months: pd.Series, mapping: dict[pd.Period, pd.Timestamp], label: str
) -> pd.Series:
    periods = pd.PeriodIndex(months.astype(str), freq="M")
    missing = sorted({str(period) for period in periods if period not in mapping})
    if missing:
        raise RuntimeError(f"Missing {label} publication dates for: {missing}")
    return pd.Series([mapping[period] for period in periods], index=months.index)
