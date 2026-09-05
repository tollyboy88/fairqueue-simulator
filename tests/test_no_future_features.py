import predictor


def test_equity_fields_are_absent_from_forecasting_features():
    joined = " ".join(predictor.FULL_FEATURES).lower()
    for forbidden in ("equity", "fairness", "deprivation", "ethnicity", "sex_disparity"):
        assert forbidden not in joined
