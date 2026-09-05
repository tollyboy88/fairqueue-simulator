import pandas as pd

from conftest import load_script

operational = load_script("04_clean_operational.py", "operational_lag")


def test_completed_quarter_is_exposed_only_in_following_quarter():
    frame = pd.DataFrame(
        {"provider_code": ["AAA"], "quarter_end": [pd.Timestamp("2024-06-30")], "value": [1.0]}
    )
    result = operational.expand_completed_quarter(frame, "quarter_end")
    assert result.month.tolist() == ["2024-07", "2024-08", "2024-09"]
