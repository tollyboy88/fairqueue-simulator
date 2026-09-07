import pandas as pd

from conftest import load_script


def test_constraint_counts_service_rows_and_provider_cap_limits_repetition():
    ranking = load_script("10_equity_constrained_ranking.py", "equity_constraint_unit")
    frame = pd.DataFrame(
        {
            "provider_code": ["A", "A", "A", "B", "C", "D"],
            "score": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
            "high_equity_need": [True, True, True, True, False, False],
        }
    )
    selected = ranking.constrained_top_k(
        frame, "score", k=4, minimum_high_need_share=0.5, max_services_per_provider=1
    )
    assert len(selected) == 4
    assert selected.high_equity_need.mean() >= 0.5
    assert selected.provider_code.value_counts().max() == 1
