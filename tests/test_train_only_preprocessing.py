import pandas as pd

import predictor


def test_imputer_statistics_are_fitted_on_training_rows_only():
    spec = predictor.model_specs()[0]
    model = predictor.build_pipeline(spec, ["breach_52w_rate"])
    train = pd.DataFrame(
        {"breach_52w_rate": [0.1, 0.2, 0.3, None], "treatment_function_code": ["A"] * 4}
    )
    test = pd.DataFrame(
        {"breach_52w_rate": [100.0], "treatment_function_code": ["A"]}
    )
    model.fit(train, [0.1, 0.2, 0.3, 0.2])
    model.predict(test)
    imputer = model.named_steps["preprocess"].named_transformers_["numeric"].named_steps["impute"]
    assert imputer.statistics_[0] == 0.2
