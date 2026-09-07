import pandas as pd

from conftest import load_script


def test_policy_snapshot_is_available_by_decision_date():
    ranking = load_script("10_equity_constrained_ranking.py", "equity_ranking")
    equity = pd.DataFrame(
        {
            "provider_code": ["A", "A"],
            "snapshot_date": pd.to_datetime(["2026-02-22", "2026-04-26"]),
            "available_date": pd.to_datetime(["2026-03-12", "2026-06-11"]),
        }
    )
    chosen = ranking.latest_available_snapshot(equity, pd.Timestamp("2026-03-31"))
    assert chosen.snapshot_date.max() == pd.Timestamp("2026-02-22")
    assert chosen.available_date.max() <= pd.Timestamp("2026-03-31")
