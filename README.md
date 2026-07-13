# FairQueue Simulator

A local, explainable simulator that ranks NHS **provider × specialty × month**
elective-care areas by combining **waiting-list pressure**, **fairness risk** and
**operational pressure** into a transparent priority score — built on public NHS
data to support fairness-aware elective prioritisation research.

> It prioritises *areas of pressure*, not individual patients.

## Quick start

```bash
pip install -r requirements.txt
python src/01_extract_data.py     # catalogue raw files
python src/02_clean_rtt.py        # build the RTT waiting-list table
```

## Where things live

```
data/raw/        426 source files, sorted into 11 categories
data/interim/    cleaned per-source tables (incl. RTT per-month cache)
data/processed/  modelling-ready parquet (rtt_provider_specialty_month.parquet …)
src/             pipeline scripts 00–08 + utils.py
app/             Streamlit app (6 pages) — to build
outputs/         data_catalogue.csv, charts, tables, rankings, metrics
notebooks/       exploration / testing
```

## Status & how to proceed

See **`BUILD_GUIDE.md`** — it tracks what's built (skeleton, data arrangement,
catalogue, RTT pipeline) and the exact next steps (WLMDS fairness → operational
cleaning → modelling join → scoring → simulation → app → exports), with the join
logic, scoring formulas and validation gates. The full design rationale is in
*Architectural Design and lay out foundation.md*.

## Data note

All inputs are public, aggregated NHS / ONS data (RTT, WLMDS, DM01 diagnostics,
A&E, KH03 beds, UEC sitrep, operating theatres, cancelled operations, ONS
population/ethnicity, IMD 2019). No patient-level data is used.
