import pandas as pd
import pytest

from conftest import load_script
from publication_dates import RTT_PUBLICATION_DATES

features = load_script("05_build_longitudinal_features.py", "feature_availability")


def test_rtt_calendar_covers_study_and_march_release_date():
    expected = pd.period_range("2022-04", "2026-06", freq="M")
    assert set(RTT_PUBLICATION_DATES) == set(expected)
    assert RTT_PUBLICATION_DATES[pd.Period("2026-03", freq="M")] == pd.Timestamp(
        "2026-05-14"
    )
    assert all(
        available > month.to_timestamp("M")
        for month, available in RTT_PUBLICATION_DATES.items()
    )


def test_feature_builder_rejects_source_published_after_forecast_date():
    frame = pd.DataFrame(
        {
            "forecast_decision_date": pd.to_datetime(["2026-05-14"]),
            "diagnostic_over_6w_rate": [0.2],
            "diagnostic_available_date": pd.to_datetime(["2026-05-15"]),
            "bed_occupancy_rate": [0.9],
            "bed_available_date": pd.to_datetime(["2026-05-01"]),
            "cancelled_operations": [10],
            "cancellation_available_date": pd.to_datetime(["2026-05-01"]),
        }
    )
    with pytest.raises(AssertionError, match="diagnostic_over_6w_rate is unavailable"):
        features.assert_sources_available(frame)
