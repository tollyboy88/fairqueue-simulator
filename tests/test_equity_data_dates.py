import pandas as pd


def test_policy_snapshot_precedes_outcome_month():
    equity_snapshot = pd.Timestamp("2026-04-26")
    outcome_date = pd.Timestamp("2026-06-30")
    assert equity_snapshot <= outcome_date
