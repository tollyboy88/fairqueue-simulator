import pandas as pd

from conftest import load_script
from publication_dates import RTT_PUBLICATION_DATES

targets = load_script("06_build_future_targets.py", "future_targets_shift")


def test_three_month_target_uses_exact_calendar_match():
    months = pd.period_range("2024-09", "2025-03", freq="M")
    release_dates = [RTT_PUBLICATION_DATES[month] for month in months]
    frame = pd.DataFrame(
        {
            "month": months.astype(str),
            "feature_date": months.to_timestamp("M"),
            "rtt_available_date": release_dates,
            "forecast_decision_date": release_dates,
            "provider_code": "AAA",
            "treatment_function_code": "C_100",
            "incomplete_total": 1000,
            "breach_52w_count": range(10, 17),
            "breach_18w_count": range(100, 107),
            "breach_52w_rate": [value / 1000 for value in range(10, 17)],
        }
    )
    result = targets.build_targets(frame, horizon=3)
    assert (result.target_date.dt.to_period("M") - result.feature_date.dt.to_period("M")).map(
        lambda offset: offset.n
    ).eq(3).all()
    october = result[result.month == "2024-10"].iloc[0]
    # October + three calendar months is January; the synthetic January count is 14.
    assert october.target_breach_52w_rate == 14 / 1000
    assert (result.forecast_decision_date < result.target_available_date).all()
