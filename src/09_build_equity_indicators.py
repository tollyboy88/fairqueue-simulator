"""Classify high equity need without assigning normative dimension weights."""
from __future__ import annotations

import pandas as pd

from utils import PROCESSED

DIMENSIONS = [
    "deprivation_disparity",
    "ethnicity_disparity",
    "age_disparity",
    "sex_disparity",
]
HIGH_NEED_PERCENTILE = 0.75


def build_indicators(disparities: pd.DataFrame, percentile: float = HIGH_NEED_PERCENTILE) -> pd.DataFrame:
    result = disparities.copy()
    flags = []
    for dimension in DIMENSIONS:
        rank = result.groupby("snapshot_date")[dimension].rank(pct=True, method="average")
        result[f"{dimension}_percentile"] = rank
        flag = rank.ge(percentile)
        result[f"high_{dimension}"] = flag
        flags.append(flag)
    result["equity_need_dimension_count"] = pd.concat(flags, axis=1).sum(axis=1)
    result["high_equity_need"] = result.equity_need_dimension_count.ge(1)
    result["high_need_percentile_cutoff"] = percentile
    return result


def main() -> None:
    disparities = pd.read_parquet(PROCESSED / "provider_disparities.parquet")
    result = build_indicators(disparities)
    result.to_parquet(PROCESSED / "equity_indicators.parquet", index=False)
    summary = result.groupby("snapshot_date").high_equity_need.mean()
    print(f"Wrote {len(result)} provider indicators across {len(summary)} snapshots")
    print(summary.to_string())


if __name__ == "__main__":
    main()
