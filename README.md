# FairQueue 2.0

FairQueue 2.0 is a research pipeline for forecasting NHS elective-care pressure and
examining transparent equity constraints. It predicts the provider–specialty 52-week
incomplete-pathway breach rate exactly three months ahead, then builds a top-*K*
monitoring list with an optional minimum share of providers with high measured equity
need.

The forecast target is independent of the policy rule. Demographic disparity indicators
are not model features: they enter only at the equity-constrained selection stage.
FairQueue prioritises aggregated service pressure, not individual patients.

## Reproduce the analysis

```powershell
py -m pip install -r requirements.txt
py run_all.py
py -m pytest -q
streamlit run app/streamlit_app.py
```

After the official source files have been downloaded once, use
`py run_all.py --skip-download` to rebuild from the recorded local files.

## Study design

- Data: 51 monthly NHS releases, April 2022–June 2026, with a SHA-256 source manifest.
- Unit: provider × treatment function × feature month.
- Outcome: 52-week breach rate at feature month + 3.
- Training features: April 2022–December 2024; targets are three months later.
- Validation features: January–June 2025; used for model selection.
- Locked test features: July 2025–March 2026; targets October 2025–June 2026.
- Equity illustration: top-20 June 2026 list using the April 2026 WLMDS snapshot.

The validation-selected Random Forest achieved test RMSE 0.0143 (1.43 percentage
points), R² 0.636, Spearman correlation 0.836, and Recall@20 0.578. Persistence had
slightly lower MAE (0.00665 versus 0.00684), so the study does not claim universal
predictive superiority. Provider-clustered bootstrap intervals and training-window,
specialty, and feature-set sensitivity analyses are retained under `outputs/metrics/`.

## Repository map

```text
src/01_download_longitudinal_data.py   official-source acquisition + manifest
src/02_clean_rtt.py ... 06_*           harmonisation, dated features, future target
src/07_* ... 12_*                      models, locked evaluation, equity, robustness
src/13_* ... 14_*                      paper figures/tables and static dashboard
tests/                                 leakage and temporal-integrity tests
app/                                   Streamlit research explorer
outputs/figures/                       three journal figures (PNG and TIFF)
outputs/tables/                        two journal tables plus policy selections
submission/Health_Systems/             submission-ready journal package
```

See `REPRODUCIBILITY.md` for the data contract and audit checks. Raw NHS downloads and
large generated Parquet files are intentionally excluded from Git; URLs, hashes, and
retrieval times are recorded in `data/source_manifest.csv`.

## Responsible-use statement

This is a retrospective, aggregate-data research prototype. It does not rank patients,
recommend treatment, make clinical decisions, estimate causal effects, or allocate NHS
capacity. Prospective operational and equity-impact evaluation would be required before
deployment.

## Licence

Code is released under the MIT Licence. NHS source data remain subject to their original
publishers' terms.
