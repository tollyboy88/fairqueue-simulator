# FairQueue: a transparent, fairness-aware simulator for prioritising NHS elective-care pressure using public data

**Authors:** Adebayo [Surname]^1^ (ORCID: [0000-0000-0000-0000])

^1^[Department, Institution, City, Country]

**Corresponding author:** Adebayo [Surname] ([email])

*Article type: Software Tool Article. Prepared for submission to F1000Research.*

---

## Abstract

**Background:** Analyses of elective-care waiting lists typically rank pressure by backlog size or by the number of patients breaching 18- or 52-week targets. These measures ignore two things that matter for fair recovery: whether some population groups are over-represented among the longest waiters, and the operational pressures (diagnostics, emergency care, beds, theatres, cancellations) that shape a provider's ability to treat. There is no openly available, transparent tool that combines waiting-list pressure, fairness risk and operational pressure to prioritise areas of the health system rather than individual patients.

**Methods:** FairQueue is a local, open-source simulator that scores every National Health Service (NHS) provider × specialty × month using only public, aggregated data. It ingests referral-to-treatment (RTT), demographic waiting-list (WLMDS), diagnostics, accident and emergency, bed occupancy, operating-theatre and cancelled-operations data, cleans and joins them, and computes three transparent sub-scores — waiting pressure, fairness risk and operational pressure — combined into a 0–100 priority score. Fairness is measured as the over-representation of deprivation, ethnicity, age and sex groups among the longest waits, and is used only in aggregate, never as individual group identity. A machine-learning model reproduces the score for new uploads and returns an explainable-AI breakdown and a bias audit.

**Results:** Across twelve months (April 2025–March 2026), FairQueue scored 41,515 provider–specialty–month areas from 152 providers and 23 specialties. Fairness-aware prioritisation changed which areas were flagged: only 25% of the top-20 overlapped with a waiting-time-only ranking, and a deprivation-weighted strategy shared none. The prediction model achieved R² = 0.96 and level accuracy 96.9%, and the fairness audit found no under-prioritisation of higher-deprivation areas.

**Conclusions:** FairQueue turns public NHS data into a transparent, explainable and fairness-aware prioritisation tool for elective-care recovery, and provides reproducible outputs for further research.

**Keywords:** elective care; waiting lists; health equity; fairness-aware prioritisation; referral to treatment; explainable artificial intelligence; NHS open data; health services research

---

## Introduction

Elective-care waiting lists in the English NHS have grown substantially, and recovery planning depends on identifying where pressure is greatest. Routine analysis and public dashboards describe waiting lists mainly through backlog counts and the proportion of patients waiting beyond the 18-week and 52-week referral-to-treatment (RTT) standards. These descriptive measures are useful but incomplete in three respects. First, they treat waiting time as the only signal, ignoring the operational context — diagnostic bottlenecks, emergency-care pressure, bed occupancy, theatre capacity and cancelled operations — that determines whether a provider can actually reduce its backlog. Second, they are silent on fairness: they do not show whether particular deprivation, ethnicity, age or sex groups are over-represented among the longest waiters, even though equitable recovery is an explicit policy aim. Third, where prioritisation or risk models exist, they are often opaque, and patient-level modelling raises data-access and ethical concerns.

Existing openly available tools tend to be descriptive dashboards over a single data source, or analytics that require patient-level records. To our knowledge there is no transparent, reproducible tool that (i) combines waiting-list, fairness and operational signals, (ii) works entirely from public aggregated data, (iii) prioritises provider × specialty areas rather than individual patients, and (iv) explains every score.

FairQueue addresses this gap. It is a local, open-source simulator that scores NHS provider × specialty × month areas by combining waiting-list pressure, fairness risk and operational pressure using visible, auditable formulas, and then lets users compare alternative prioritisation strategies. It adds an automated data-preparation engine that cleans and joins heterogeneous uploaded datasets, and a machine-learning model with an explainable-AI layer and a built-in bias audit so that predictions on new data remain transparent and equity-aware. Importantly, FairQueue prioritises areas of pressure, not individual patients, keeping it within the bounds of safe, public-data health-services research.

## Methods

### Implementation

**Data sources and unit of analysis.** FairQueue uses only public, aggregated data published by NHS England, the Office for National Statistics (ONS) and the Ministry of Housing, Communities and Local Government (MHCLG). The core unit is the *provider × specialty × month*, chosen because RTT data are reported monthly at provider and treatment-function (specialty) level. Eleven source families are used: RTT pathways (waiting pressure); the Waiting List Minimum Data Set, WLMDS (fairness); monthly diagnostics (DM01), A&E attendances and emergency admissions, bed availability and occupancy (KH03), urgent and emergency care daily situation reports, operating theatres and cancelled elective operations (operational pressure); and ONS population, ONS ethnicity and the 2019 Index of Multiple Deprivation (context). No patient-level data are used.

**Cleaning and joining.** Each source is parsed into a standardised table keyed by NHS provider code, and where available treatment-function code and reporting month. Provider-level operational measures are applied to all of a provider's specialty rows for the month; quarterly sources (beds, theatres, cancellations) are mapped to each month in the NHS financial-year quarter (Q1 = April–June, … Q4 = January–March). Aggregate specialty rows are removed to avoid double counting. All sources are left-joined onto the RTT base grid to form a single modelling dataset.

**Feature engineering and scoring.** Waiting-pressure components (18- and 52-week breach rates, decision-to-admit pressure, new-demand pressure, throughput and month-on-month backlog growth) are engineered from RTT counts. Fairness components are computed as *fairness gaps* — for each demographic group, its share of the longest waits (>52 weeks) minus its share of all waits — taking the maximum positive gap per dimension (deprivation, ethnicity, age) and the absolute male–female difference for sex, plus a missing-demographic term. Operational components combine the diagnostic six-week breach rate, bed occupancy, an A&E pressure index, a cancellation-disruption index and a theatre-capacity index. Every component is winsorised at the 1st and 99th percentiles and min–max normalised to 0–1. The three sub-scores use fixed, published weights and are combined into the final priority score:

- waiting_pressure = 0.30·breach18w + 0.25·breach52w + 0.15·DTA + 0.15·backlog growth + 0.10·demand + 0.05·(1−throughput)
- fairness_risk = 0.30·deprivation + 0.25·ethnicity + 0.20·age + 0.15·sex + 0.10·missing-demographic
- operational_pressure = 0.25·diagnostic + 0.25·bed + 0.20·A&E + 0.15·cancellation + 0.15·theatre
- **final_priority_score = (0.50·waiting_pressure + 0.30·fairness_risk + 0.20·operational_pressure) × 100**

Scores are banded Lower (0–39), Moderate (40–59), High (60–79) and Critical (80–100).

**Simulation.** Five prioritisation strategies are computed and ranked within each month: (1) waiting-time only, (2) operational, (3) cancellation-aware, (4) deprivation-weighted and (5) the full fairness-aware model. Comparison metrics include rank shift, top-20 overlap, fairness/operational/cancellation lift and sensitivity of the top-20 to four weighting scenarios.

**Prediction and explainable AI.** A RandomForest regressor learns the mapping from real-world features (breach rates, decision-to-admit, demand, throughput, backlog growth, fairness gaps, diagnostics, beds, A&E, cancellations, theatres) to the 0–100 priority, so a provider can score new uploads consistently. Each prediction is explained by a dependency-free *drop-to-median* attribution — each feature's contribution is the change in the prediction when that feature is reset to its typical value — alongside global feature importance. Crucially, protected characteristics never enter the model as raw group identity; they enter only as aggregate over-representation gaps, which raise priority for under-served areas. A built-in audit reports the correlation of each fairness gap with predicted priority and checks that higher-deprivation areas are not under-prioritised.

**Auto-ingest engine.** A separate engine reproduces the cleaning-and-joining pipeline on arbitrary uploads: it detects each file's type from its name and column signatures, cleans it, and joins the results into the provider × specialty × month structure for immediate scoring or prediction.

### Operation

**Minimal requirements.** Python 3.11 or 3.12 (64-bit) and the packages listed in `requirements.txt` (pandas, numpy, openpyxl, xlrd, pyarrow, streamlit, plotly, scikit-learn, joblib, python-docx, jinja2). Approximately 2 GB free disk and 4 GB RAM are sufficient; no internet connection or database is required. The tool is written entirely in open-source Python.

**Installation and running.** After `pip install -r requirements.txt`, the full pipeline is rebuilt with `python run_all.py`, which writes the processed datasets and outputs. The interactive application is launched with `python -m streamlit run app/streamlit_app.py` (opens at `http://localhost:8501`); a self-contained static dashboard (`outputs/FairQueue_Dashboard.html`) can also be opened directly in a browser with no server.

**Workflow.** The eight-page application comprises: National Overview, Provider–Specialty Ranking, Fairness Analysis, Operational Pressure, Simulation Comparison, Explanation, Data Preparation (upload → auto clean/join) and Predict & Explain (model + explainable-AI report). The two upload pages accept Excel (.xlsx/.xls), CSV and Word (.docx) files; a Word rubric can supply a dictionary of feature weights used to produce a transparent, user-defined score alongside the model prediction. Figure 1 shows the architecture and workflow.

## Results

FairQueue was applied to twelve consecutive months of published data (April 2025 to March 2026). After cleaning and joining, the modelling dataset contained 41,515 provider–specialty–month records covering 152 providers and 23 specialties. National RTT incomplete pathways fell from approximately 7.0 million to 6.6 million over the year, and the share treated within 18 weeks rose from 58.8% to 64.7% (Figure 2). All automated data-quality, score-range and logic checks passed (no negative counts, no impossible breach values, all normalised scores within 0–1, final scores within 0–100, and priority bands consistent with score ranges).

**Fairness-aware prioritisation changes which areas are flagged.** Comparing each strategy's top-20 areas with a waiting-time-only ranking (Table 2, Figure 3), the full fairness-aware model shared only 25% of its top-20 with the waiting-time-only list, and the deprivation-weighted strategy shared none (0%). The fairness lift — the difference in mean fairness risk between the fairness-aware and waiting-time-only top-20 — was +0.43, and the cancellation-aware strategy raised mean cancellation pressure in its top-20 by +0.42 relative to waiting-time-only. Under four weighting scenarios, 60–70% of the top-20 remained stable, and 25% of areas were common to all scenarios, indicating a robust core of high-priority areas together with a fairness-sensitive margin. The distribution of rank shifts (Figure 4) shows many areas rising once fairness and operational pressure are included.

**The prediction model is accurate and equitable.** The RandomForest reproduced the priority score with R² = 0.96 and mean absolute error 1.14 points (out of 100), and predicted the priority band with 96.9% accuracy on held-out data (Table 3). Global importance was led by the 18-week breach rate, decision-to-admit pressure, new demand and the 52-week long-wait rate, with fairness gaps contributing meaningfully. The fairness audit returned positive correlations between every fairness gap and predicted priority (deprivation +0.22, age +0.21, ethnicity +0.18, sex +0.16) and found no deprivation bias: mean predicted priority did not fall for higher-deprivation areas.

**Table 1. Priority-score components and weights.**

| Sub-score (weight in final) | Components (within-score weights) |
|---|---|
| Waiting pressure (0.50) | 18-week breach 0.30; 52-week 0.25; DTA 0.15; backlog growth 0.15; demand 0.10; inverse throughput 0.05 |
| Fairness risk (0.30) | Deprivation 0.30; ethnicity 0.25; age 0.20; sex 0.15; missing-demographic 0.10 |
| Operational pressure (0.20) | Diagnostic 0.25; bed 0.25; A&E 0.20; cancellation 0.15; theatre 0.15 |

**Table 2. Strategy comparison against waiting-time-only prioritisation (latest month).**

| Strategy | Top-20 overlap with waiting-time-only | Key lift |
|---|---|---|
| Operational | 0.50 | operational lift +0.11 |
| Cancellation-aware | 0.40 | cancellation impact +0.42 |
| Deprivation-weighted | 0.00 | — |
| Full fairness-aware (proposed) | 0.25 | fairness lift +0.43 |

**Table 3. Prediction model performance and fairness audit.**

| Metric | Value |
|---|---|
| R² (held-out) | 0.96 |
| Mean absolute error | 1.14 points (0–100) |
| Priority-band accuracy | 96.9% |
| Corr(deprivation gap, predicted priority) | +0.22 |
| Corr(age / ethnicity / sex gap, priority) | +0.21 / +0.18 / +0.16 |
| Deprivation bias detected | No |

## Use Cases

**Use case 1 — preparing a provider's raw data.** A provider holds several raw NHS files (for example an RTT *Incomplete-Provider* workbook, a monthly diagnostics *Provider* file and a cancelled-operations CSV). On the Data Preparation page these are uploaded together; the engine detects each file type, cleans it, and joins them into a provider × specialty × month table with engineered features. In testing, an RTT file (3,496 rows), a diagnostics file and a cancellations file were detected and joined automatically, and the cleaned dataset was downloadable as CSV.

**Use case 2 — scoring and ranking.** The Provider–Specialty Ranking page lists areas by priority for a chosen month, with filters for level, specialty and provider, and a downloadable ranking. The Simulation Comparison page shows how the ranking changes across strategies and highlights the biggest movers under the fairness-aware model.

**Use case 3 — prediction with explanation.** On the Predict & Explain page a user scores the prepared data, an uploaded feature table, or a built-in sample. Each area receives a predicted priority and band; selecting an area shows the top contributing drivers (in points), and a comprehensive HTML report bundles the predictions, global drivers and fairness audit. An optional Word (.docx) rubric supplies feature weights, producing a transparent rubric-weighted score next to the model prediction. Example input (`samples/example_features.csv`) and rubric (`samples/example_rubric.docx`) files are provided.

## Discussion and Conclusions

FairQueue demonstrates that public, aggregated NHS data are sufficient to build a transparent, fairness-aware and explainable prioritisation tool for elective-care recovery. Because every score is a visible weighted sum of normalised, publicly sourced metrics, the reasoning behind each ranking can be inspected and challenged — a deliberate contrast with opaque risk models. The empirical finding that fairness-aware prioritisation shares only a quarter of its top-20 with a waiting-time-only ranking suggests that equity considerations materially change where recovery effort would be directed, and that these effects are robust to reasonable changes in weighting.

Several limitations should guide interpretation. FairQueue prioritises provider × specialty *areas*, not individual patients; it is a decision-support and research tool, not an automated allocation system, and clinical urgency at the individual level is out of scope by design. Fairness is derived from a WLMDS snapshot and is treated as a structural provider-level measure applied across months; population context from ONS and IMD is offered as context only, because provider catchments do not map cleanly onto local-authority boundaries. Some operational measures are available only at provider level and are applied across all of a provider's specialties, and quarterly sources are expanded to monthly. Global min–max normalisation compresses the composite score, so most areas fall in the Lower/Moderate bands and the value lies in relative ranking and rank shifts rather than absolute band labels; per-period normalisation is a straightforward alternative. The prediction model learns the transparent score and therefore inherits its assumptions; it is intended to generalise scoring to new uploads, not to introduce a separate black-box judgement.

Fairness is implemented so as to promote equity without discrimination: protected characteristics are used only as aggregate over-representation gaps, never as individual group identity, and the built-in audit checks that under-served areas are not disadvantaged. Future work includes optional per-period normalisation, forecasting of future pressure, an optional SQL back-end, and broader validation with domain experts. In conclusion, FairQueue provides an open, reproducible route from public NHS data to a fairness-aware prioritisation of elective-care pressure, with explainable predictions and auditable equity properties.

## Data and Software Availability

**Underlying data.** No new primary data were generated. All inputs are public, aggregated data published by NHS England, the Office for National Statistics and the Ministry of Housing, Communities and Local Government, and contain no patient-identifiable information. The specific collections used are RTT waiting times, monthly diagnostics (DM01), A&E attendances and emergency admissions, bed availability and occupancy (KH03), urgent and emergency care daily situation reports, operating theatres, and cancelled elective operations (all NHS England); ONS mid-year population and Census 2021 ethnicity estimates; and the English Indices of Deprivation 2019 (MHCLG). Access points are listed in the References.

**Extended data.** [Zenodo]. FairQueue Simulator: processed datasets, data catalogue and result tables. [DOI to be inserted on archiving]. This archive contains the processed provider × specialty × month modelling dataset, priority and strategy-comparison tables, the data catalogue (`data_catalogue.csv`), exported metrics and figures. Data are available under the terms of the Creative Commons Attribution 4.0 International licence (CC-BY 4.0).

**Software availability.**

- Source code available from: [https://github.com/[username]/fairqueue-simulator] (to be inserted).
- Archived source code at time of publication: [Zenodo DOI to be inserted].
- License: MIT License (OSI-approved).

Software was implemented in Python 3 using pandas, numpy, openpyxl, xlrd, pyarrow, scikit-learn, joblib, python-docx, Streamlit, Plotly and Jinja2. Version numbers are recorded in `requirements.txt`.

## Author contributions

Author contributions will be recorded on submission using the CRediT taxonomy. Suggested contributions for Adebayo [Surname]: Conceptualization; Methodology; Software; Formal Analysis; Data Curation; Visualization; Writing – Original Draft Preparation; Writing – Review & Editing. (Add co-authors and their roles as applicable.)

## Competing interests

No competing interests were disclosed.

## Grant information

The author(s) declared that no grants were involved in supporting this work.

## Acknowledgments

The author thanks NHS England, the Office for National Statistics and the Ministry of Housing, Communities and Local Government for making the underlying data openly available.

## References

1. NHS England. Consultant-led Referral to Treatment (RTT) Waiting Times statistics. Available at: <https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/>
2. NHS England. Monthly Diagnostics Waiting Times and Activity (DM01). Available at: <https://www.england.nhs.uk/statistics/statistical-work-areas/diagnostics-waiting-times-and-activity/monthly-diagnostics-waiting-times-and-activity/>
3. NHS England. A&E Attendances and Emergency Admissions. Available at: <https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/>
4. NHS England. Bed Availability and Occupancy Data (KH03). Available at: <https://www.england.nhs.uk/statistics/statistical-work-areas/bed-availability-and-occupancy/>
5. NHS England. Cancelled Elective Operations (QMCO). Available at: <https://www.england.nhs.uk/statistics/statistical-work-areas/cancelled-elective-operations/>
6. Office for National Statistics. Census 2021 and population estimates, England and Wales. Available at: <https://www.ons.gov.uk/>
7. Ministry of Housing, Communities & Local Government. English Indices of Deprivation 2019. Available at: <https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019>
8. Breiman L. Random Forests. Machine Learning. 2001;45(1):5–32. <https://doi.org/10.1023/A:1010933404324>
9. NISO. CRediT — Contributor Roles Taxonomy. Available at: <https://credit.niso.org/>

*Note to authors: add domain-specific references on elective-care recovery, waiting-list equity and algorithmic fairness as appropriate before submission.*

## Figure legends

**Figure 1. FairQueue architecture and workflow.** Public NHS and ONS sources are cleaned and joined (by the pipeline or the auto-ingest engine) into a provider × specialty × month modelling dataset, scored by transparent weighted formulas, compared across five strategies, modelled for prediction with explainable AI, and surfaced through an eight-page application and static dashboard.

**Figure 2. National RTT waiting-list trend, 2025/26.** Monthly incomplete pathways and numbers waiting over 18 and 52 weeks, April 2025 to March 2026.

**Figure 3. Top-20 overlap between each strategy and waiting-time-only prioritisation.** Lower overlap indicates a strategy that changes which areas are prioritised.

**Figure 4. Rank shift under the full fairness-aware model versus waiting-time-only.** Positive values indicate areas that rise in priority once fairness and operational pressure are included.

**Figure 5. Top 10 priority provider–specialty areas under the full fairness-aware model (latest month).**
