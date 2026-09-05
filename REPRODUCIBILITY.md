# Reproducibility and audit trail

## Data contract

`data/source_manifest.csv` records every official NHS download used by the pipeline,
including the source URL, local relative path, byte size, retrieval timestamp, and
SHA-256 digest. The model uses public aggregate data only; no patient-level records or
special-category personal data are processed.

RTT monthly releases are harmonised to one provider–treatment-function row per month.
The target is joined by exact calendar key at month + 3; it is never derived from the
same row as the predictor. Rows require at least 100 incomplete pathways in both feature
and target months. DM01 is lagged one month and quarterly beds/cancellations are lagged
one completed quarter before joining.

## Split contract

Splits are defined by feature date, not by random row sampling; every corresponding
outcome remains exactly three calendar months later:

| Partition | Feature months | Target months | Use |
|---|---|---|---|
| Training | April 2022–December 2024 | July 2022–March 2025 | Fit candidates and preprocessors |
| Validation | January–June 2025 | April–September 2025 | Choose the model family |
| Test | July 2025–March 2026 | October 2025–June 2026 | One final held-out evaluation |

All imputers, scalers, encoders, and estimators are fitted on development data only.
Provider-clustered bootstrap intervals use 100 reproducible resamples.

## Integrity tests

Run `py -m pytest -q`. The tests check:

- split chronology and non-overlapping feature windows;
- exact three-calendar-month target shifting;
- prohibition of future/target fields in the feature matrix;
- quarterly operational-release lags;
- train-only preprocessing;
- availability of equity data before the evaluated outcome.

## Key outputs

- `outputs/metrics/test_model_metrics.csv`: locked test results for all candidates.
- `outputs/metrics/bootstrap_confidence_intervals.csv`: provider-clustered uncertainty.
- `outputs/metrics/ablation_results.csv`: RTT-only versus operational feature sets.
- `outputs/metrics/training_window_robustness.csv`: post-April-2023 sensitivity.
- `outputs/metrics/equity_utility_tradeoff.csv`: top-20 policy frontier.
- `outputs/figures/`: the three manuscript figures in PNG and 300-dpi TIFF.

The selected-model artifact stores the full preprocessing-and-estimation pipeline in
`models/fairqueue_forecaster.joblib`.

## Determinism and environment

Random seeds are fixed in the modelling scripts. Exact numerical reproduction can still
vary slightly by Python, BLAS, and package version. Install the declared minimum versions
from `requirements.txt`, preserve the source-manifest files, and record `pip freeze` for
an archival run.
