# Reproducibility and audit trail

## Data contract

`data/source_manifest.csv` records every official NHS download used by the pipeline,
including the source URL, local relative path, byte size, retrieval timestamp, and
SHA-256 digest. The model uses public aggregate data only; no patient-level records or
special-category personal data are processed.

RTT monthly releases are harmonised to one provider–treatment-function row per month.
The target is joined by exact calendar key at month + 3; it is never derived from the
same row as the predictor. Rows require at least 100 incomplete pathways in both feature
and target months. Each reporting month is paired with its pre-announced official
publication date. DM01, beds and cancellations are joined only when their recorded
publication date is on or before the corresponding RTT forecast date.

## Split contract

Splits are defined by feature date, not by random row sampling; every corresponding
outcome remains exactly three reporting months later:

| Partition | Feature reporting months | Forecast release dates | Target reporting months | Use |
|---|---|---|---|---|
| Training | April 2022–December 2024 | June 2022–February 2025 | July 2022–March 2025 | Fit candidates and preprocessors |
| Validation | January–June 2025 | March–August 2025 | April–September 2025 | Choose the model family |
| Test | July 2025–March 2026 | September 2025–14 May 2026 | October 2025–June 2026 | One final held-out evaluation |

All imputers, scalers, encoders, and estimators are fitted on development data only.
Provider-clustered bootstrap intervals use 1,000 reproducible resamples. The same
provider resample is used for paired differences between Random Forest and Persistence.

## Integrity tests

Run `py -m pytest -q`. The tests check:

- split chronology and non-overlapping feature windows;
- exact three-calendar-month target shifting;
- prohibition of future/target fields in the feature matrix;
- quarterly operational-release lags;
- train-only preprocessing;
- exact RTT publication-calendar coverage, including the 14 May 2026 March release;
- availability of every populated operational input and equity snapshot on or before
  the forecast decision date.

## Key outputs

- `outputs/metrics/test_model_metrics.csv`: locked test results for all candidates.
- `outputs/metrics/bootstrap_confidence_intervals.csv`: provider-clustered uncertainty.
- `outputs/metrics/paired_bootstrap_differences.csv`: paired differences in MAE, RMSE,
  and NDCG@20 for Random Forest minus Persistence.
- `outputs/metrics/ablation_results.csv`: RTT-only versus operational feature sets.
- `outputs/metrics/training_window_robustness.csv`: post-April-2023 sensitivity.
- `outputs/metrics/equity_pressure_capture_frontier.csv`: top-20 policy frontier.
- `outputs/metrics/provider_cap_sensitivity.csv`: limits on specialties per provider.

The model artifact records Persistence as the primary validation-selected forecaster and
stores the full Random Forest preprocessing-and-estimation pipeline as the selected
learned comparator in `models/fairqueue_forecaster.joblib`.

The June 2026 equity illustration is generated at the 14 May 2026 forecast decision
date—the official publication date for March 2026 RTT statistics. It uses the WLMDS v2
file for the 29 March 2026 provider-demographics snapshot, available on 14 May. Snapshot
date and availability date are retained separately, and the later April release is
excluded. The code requires every source availability date to be no later than the RTT
forecast date, rather than merely earlier than the outcome month.

## Determinism and environment

Random seeds are fixed in the modelling scripts. Exact numerical reproduction can still
vary slightly by Python, BLAS, and package version. Install the declared minimum versions
from `requirements.txt`, preserve the source-manifest files, and record `pip freeze` for
an archival run.
