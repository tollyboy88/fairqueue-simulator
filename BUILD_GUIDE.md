# FairQueue Simulator — Build Guide & Foundation Instructions

A working roadmap for building the simulator from the *Architectural Design and
lay-out foundation* blueprint. This file is the single source of truth for **how
to go about the project**: what is already built, what to build next, and exactly
how each piece fits together. Update the status boxes as you go.

---

## 0. What the project is

A **local** simulator that ranks NHS **provider × specialty × month** areas by
combining three transparent signals into a final priority score:

```
final_priority_score = 0.50 × waiting_pressure
                     + 0.30 × fairness_risk
                     + 0.20 × operational_pressure   (×100, banded Lower→Critical)
```

It does **not** prioritise individual patients. It answers: *which NHS
provider-specialty areas have high waiting-list pressure, high operational
pressure and high fairness risk?* — and lets you compare five prioritisation
strategies, so the results can support a journal paper.

Stack: Python · pandas · Parquet · Streamlit · Plotly · (scikit-learn later).
Storage: local Parquet first; SQL Server only as an optional later version.

---

## 1. Current status

| Step | Deliverable | Status |
|------|-------------|--------|
| Project skeleton | `data/ src/ app/ outputs/ notebooks/`, `requirements.txt`, `README.md`, `.gitignore` | ✅ Done |
| Arrange raw data | All **426** files sorted into `data/raw/<category>/` | ✅ Done |
| Catalogue | `outputs/data_catalogue.csv` (every file + source + period) | ✅ Done |
| RTT cleaning | `data/processed/rtt_provider_specialty_month.parquet` (41,515 rows, 12 months) | ✅ Done |
| WLMDS fairness | `wlmds_fairness.parquet` (+ detail) — 176 providers | ✅ Done |
| Operational cleaning | diagnostics / A&E / beds / theatres / cancelled → `operational_pressure.parquet` | ✅ Done |
| Modelling dataset | `modelling_dataset.parquet` (one big join, normalised) | ✅ Done |
| Scoring engine | `priority_scores.parquet` (3 sub-scores + final + level) | ✅ Done |
| Simulation engine | `strategy_comparison.parquet` (5 strategies + ranks/shifts) | ✅ Done |
| Validation | `outputs/metrics/validation_report.txt` (ALL PASS) | ✅ Done |
| Streamlit app | 6 pages (`app/`) — all smoke-tested | ✅ Done |
| Static dashboard | `outputs/FairQueue_Dashboard.html` (open in browser, no server) | ✅ Done |
| Export results | top-20, lifts, sensitivity, charts, notebook | ✅ Done |

### How to view the dashboard

```bash
pip install -r requirements.txt
python run_all.py                       # rebuilds every parquet + outputs

# Option A — no server: open the static dashboard
open outputs/FairQueue_Dashboard.html   # (or double-click it)

# Option B — full interactive app (6 pages, filters, downloads)
streamlit run app/streamlit_app.py
```

---

## 2. Data map (raw → category → what it feeds)

Each folder under `data/raw/` corresponds to one source. File counts are from the
arrangement step; see `outputs/data_catalogue.csv` for the per-file detail.

| `data/raw/` folder | Files | Feeds | Grain |
|--------------------|------:|-------|-------|
| `rtt/` | 108 | Waiting pressure (core table) | provider × specialty × month |
| `wlmds/` | 5 | Fairness risk (age/sex/ethnicity/deprivation) | provider/specialty × demographic |
| `diagnostics/` | 40 | Operational: diagnostic bottleneck (DM01) | provider × month |
| `ae_emergency/` | 55 | Operational: A&E / emergency pressure | provider × month |
| `beds_kh03/` | 64 | Operational: bed occupancy | provider × quarter |
| `uec_sitrep/` | 76 | Operational: urgent-care bed pressure | provider × day → month |
| `operating_theatres/` | 34 | Operational: theatre capacity | provider × quarter |
| `cancelled_operations/` | 35 | Operational: cancellation disruption | provider × quarter |
| `ons_population/` | 3 | Population context | LA / area |
| `ons_ethnicity/` | 4 | Ethnicity context | LA / area |
| `imd/` | 2 | Deprivation context | LSOA / LA |

**Join keys** (use code, never name alone):

```
month + provider_code + treatment_function_code   ← RTT, WLMDS-by-specialty
month + provider_code                              ← provider-level operational data
```

Quarterly sources (beds, theatres, cancelled ops) map to every month in the
quarter: `Q1 = Apr-Jun, Q2 = Jul-Sep, Q3 = Oct-Dec, Q4 = Jan-Mar` (NHS financial
year). Provider-level pressure (e.g. bed occupancy) is applied to **all** that
provider's specialty rows for the month.

---

## 3. Pipeline scripts (`src/`)

Run in order. Each writes Parquet so later steps just reload.

```
00_arrange_raw_data.py   ✅ zip → data/raw/<category>/ (resumable, per-category arg)
01_extract_data.py       ✅ data/raw → outputs/data_catalogue.csv
02_clean_rtt.py          ✅ RTT → rtt_provider_specialty_month.parquet (per-month cache)
03_clean_wlmds.py        ⬜ WLMDS → wlmds_fairness.parquet
04_clean_operational.py  ⬜ diagnostics/A&E/beds/theatres/cancelled → *_pressure.parquet
05_build_features.py     ⬜ join all → modelling_dataset.parquet (+ normalise/winsorise)
06_scoring_engine.py     ⬜ scores → priority_scores.parquet
07_simulation_engine.py  ⬜ 5 strategies → strategy_comparison.parquet
08_validation_checks.py  ⬜ data/score/logic checks (formalise §17 of blueprint)
utils.py                 ✅ paths, calendar/quarter, header finder, minmax, winsorise…
```

**RTT cleaning notes (already implemented in `02_clean_rtt.py`):**
- Header is row 14; data from row 15. Read the `Provider` sheet (and
  `Provider with DTA`) — **not** `IS Provider` (independent sector).
- `breach_18w_count = incomplete_total − "Total within 18 weeks"`.
- `breach_52w_count = "Total 52 plus weeks"`.
- Drop aggregate specialty rows (TFC `C_999` / "Total") to avoid double counting.
- Admitted / NonAdmitted totals = `"Total number of completed pathways (all)"`;
  new demand = `"Number of new RTT clock starts during the month"`.

---

## 4. Build order (do these next, smallest-risk first)

1. **WLMDS fairness (`03_clean_wlmds.py`).** Inspect the 5 WLMDS files
   (`data/raw/wlmds/`). For each demographic group compute
   `share_of_long_waits − share_of_all_waits` (the *fairness gap*). Output one row
   per provider/specialty × demographic with the gap, plus a
   `missing_demographic_score`. Fairness sub-scores = max positive gap per
   dimension (sex = absolute male/female difference).
2. **Operational cleaning (`04_clean_operational.py`).** One function per source,
   each returning `provider_code, month, <score>`:
   diagnostic_over_6w_rate · ae_pressure_score · bed_occupancy_rate ·
   theatre_pressure_score · cancellation_pressure_score. Expand quarterly→monthly.
3. **Modelling dataset (`05_build_features.py`).** Left-join everything onto the
   RTT table by the keys in §2; engineer waiting-pressure components
   (breach rates, DTA pressure, demand, throughput, backlog growth); winsorise
   (1st/99th pct) then min-max normalise every component to 0–1.
4. **Scoring engine (`06_scoring_engine.py`).** Apply the three sub-score formulas
   and the final weighted score; band into Lower/Moderate/High/Critical.
5. **Simulation engine (`07_simulation_engine.py`).** Compute all five strategies
   and the comparison metrics (rank shift, top-k overlap, fairness/operational/
   cancellation lift, sensitivity stability).
6. **Streamlit app (`app/`).** Build page 2 (Provider-Specialty Ranking) first —
   it only needs `priority_scores.parquet` — then add the other five pages.
7. **Export (`outputs/`).** `top_20_priority_areas.csv`, `strategy_comparison.csv`,
   `fairness_lift_results.csv`, `sensitivity_analysis.csv`, and charts for the paper.

---

## 5. Scoring reference (from the blueprint)

```
waiting_pressure  = 0.30·breach_18w_rate + 0.25·breach_52w_rate + 0.15·dta_pressure
                  + 0.15·backlog_growth + 0.10·demand + 0.05·inverse_throughput
fairness_risk     = 0.30·deprivation + 0.25·ethnicity + 0.20·age
                  + 0.15·sex + 0.10·missing_demographic
operational       = 0.25·diagnostic + 0.25·bed + 0.20·ae
                  + 0.15·cancellation + 0.15·theatre
final             = 0.50·waiting + 0.30·fairness + 0.20·operational   (×100)
```

Bands: `0–39 Lower · 40–59 Moderate · 60–79 High · 80–100 Critical`.

Five strategies to compare: (1) waiting-time only, (2) +operational,
(3) cancellation-aware, (4) deprivation-weighted, (5) full fairness-aware (the
proposed model). Definitions in §14 of the blueprint.

---

## 6. Validation gates (must pass before trusting results)

Data: no negative counts · no rates > 100% · consistent provider codes · valid
months · correct quarter mapping · no double-counted totals · documented missing
values. Scores: every normalised score in 0–1 · final score 0–100 · bands match
ranges · no provider duplicated for a month+specialty. Logic: high 52-week waits ↑
priority · high cancellation ↑ operational · high missing-demographic ↑ fairness
uncertainty · low throughput ↑ waiting pressure.

*RTT table already passes the data gates (0 negatives, 0 impossible breaches,
0 duplicates, 12 months × 152 providers × 23 specialties).*

---

## 7. From simulator to paper

The simulator is the evidence engine for the journal paper. Target outputs:
- **Headline result:** how much fairness-aware scoring changes prioritisation vs.
  waiting-time-only (rank shift + top-20 overlap).
- **Fairness lift:** average fairness risk captured in the top-20 fairness-aware
  list minus the waiting-time-only list.
- **Cancellation impact** and **operational lift** — same comparison logic.
- **Sensitivity:** stability of the top-20 across the four weight scenarios (§16).
- **Worked explanations:** per-area driver breakdowns (page 6) as illustrative
  case studies.

Keep every exported table and chart in `outputs/` with the weight settings
recorded, so figures are reproducible for the manuscript.

---

## 8. How to run

```bash
pip install -r requirements.txt

python src/00_arrange_raw_data.py      # already done (idempotent)
python src/01_extract_data.py          # catalogue
python src/02_clean_rtt.py             # RTT parquet (per-month cache; re-run to resume)
# …add 03–08 as built…

streamlit run app/streamlit_app.py     # once the app exists
```

Heavy Excel reads are cached per month under `data/interim/`, so re-running a
script resumes instead of repeating work.

---

## Models added (app pages 7 & 8)

Two additional models are wired into the app as new pages.

**Page 7 — Data Preparation (`src/ingest_engine.py`).** A healthcare provider can
upload several raw datasets (Excel / CSV). The engine detects what each file is
(RTT incomplete, diagnostics, A&E, cancelled operations, …) from filename and
header signatures, cleans each, and joins them into the provider × specialty ×
month structure — the same clean/join logic the pipeline applies to the data
folder, but on arbitrary uploads. Output is downloadable and feeds page 8.

**Page 8 — Predict & Explain (`src/predictor.py`, `src/12_train_model.py`).** A
RandomForest predicts the 0–100 fairness-aware priority for each provider ×
specialty area (R² = 0.96, MAE ≈ 1.1 pts, level accuracy ≈ 97%). It accepts
Excel / CSV feature tables and an optional Word (.docx) rubric of feature weights.
Every prediction comes with an **explainable-AI** breakdown (drop-to-median
attribution — each feature's points contribution), global importance, and a
downloadable comprehensive HTML report.

**Fairness without bias.** Protected characteristics are never used as raw group
identity — only as *aggregate over-representation gaps* (a group's share of the
longest waits minus its share of all waits). These raise priority for under-served
areas (equity-promoting). The built-in audit checks that higher-deprivation areas
are not under-prioritised and reports the fairness-gap/priority correlations.

Pre-trained model: `models/fairqueue_model.joblib` (retrains automatically if
missing). Example uploads to try the pages: `samples/example_features.csv`,
`samples/example_rubric.docx`.
