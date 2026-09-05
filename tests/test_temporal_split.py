import pandas as pd

from conftest import load_script

targets = load_script("06_build_future_targets.py", "future_targets")


def test_split_boundaries_are_strictly_chronological():
    dates = pd.Series(
        pd.to_datetime(["2024-12-31", "2025-01-31", "2025-06-30", "2025-07-31", "2026-03-31"])
    )
    assert targets.assign_split(dates).tolist() == [
        "train",
        "validation",
        "validation",
        "test",
        "test",
    ]
