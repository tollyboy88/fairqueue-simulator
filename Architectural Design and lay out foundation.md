## **A to Z Project Blueprint** 

## **Project name** 

## **FairQueue Simulator** 

## **Core purpose** 

To build a local simulator app that proves whether public NHS data can be used to prioritise elective care pressure areas more fairly. 

The app will not prioritise individual patients. It will prioritise: 

## **Provider × Specialty × Month or Quarter** 

Example: 

```
Leeds Teaching Hospitals NHS Trust
Trauma and Orthopaedics
March 2026
Priority level: Critical
```

The simulator will answer: 

**Which NHS provider-specialty areas have high waiting-list pressure, high operational pressure and high fairness risk?** 

## **1. The gap this prototype is covering** 

Most elective waiting-list analysis focuses on simple backlog measures: 

```
How many patients are waiting?
How many are waiting over 18 weeks?
How many are waiting over 52 weeks?
```

That is useful, but incomplete. 

Your simulator covers these gaps: 

## **Gap** 

Waiting-time analysis often ignores fairness Backlog analysis often ignores operational pressure Prioritisation is often not transparent Public data is often used descriptively only 

AI models can be black-box Patient-level data is hard to access 

## **What your simulator adds** 

Adds age, sex, ethnicity and deprivation fairness risk 

Adds diagnostics, A&E, beds, theatre capacity and cancelled operations Uses visible formulas and explainable scoring 

Turns public NHS data into an interactive simulator 

Starts with transparent scoring before optional machine learning Uses public aggregated NHS data safely 

## **2. Final architecture design** 

```
Raw Public Data
RTT, WLMDS, ONS, IMD, Diagnostics, A&E, Beds, Theatres, Cancelled Ops
        |
        v
Data Ingestion Layer
Read Excel, CSV, ZIP files
        |
        v
Data Cleaning Layer
Standardise dates, provider codes, specialties, counts and waiting bands
        |
        v
Local Processed Storage
Parquet files or SQL Server tables
        |
        v
Feature Engineering Layer
Waiting pressure, fairness risk and operational pressure features
        |
        v
Scoring Engine
Calculate priority scores using transparent formulas
        |
        v
Simulation Engine
Compare different prioritisation strategies
        |
        v
Streamlit App
Dashboard, ranking, fairness page, operational pressure page, simulation
page
        |
        v
Outputs
Charts, tables, rankings, metrics and results for later journal paper
```

## **3. Storage decision** 

Use **local storage first** . 

Best setup: 

```
Python
Pandas
Parquet
Streamlit
Plotly
Scikit-learn later if needed
```

Use SQL Server only after the first working version. 

## **Why local storage first?** 

Because this is a simulator, not a production NHS system. 

Local Parquet files are enough because they are: 

```
fast
simple
easy to debug
easy to reload in Streamlit
good for research prototypes
```

## **Recommended route** 

```
Version 1: Local CSV and Parquet
Version 2: Optional SQL Server
Version 3: Optional forecasting or machine learning
```

## **4. Folder structure** 

Create this project folder: 

```
fairqueue-simulator/
│
├── data/
│   ├── raw/
│   │   ├── rtt/
│   │   ├── wlmds/
│   │   ├── ons_population/
│   │   ├── ons_ethnicity/
│   │   ├── imd/
│   │   ├── diagnostics/
│   │   ├── ae_emergency/
│   │   ├── beds_kh03/
│   │   ├── uec_sitrep/
│   │   ├── operating_theatres/
│   │   └── cancelled_operations/
│   │
│   ├── interim/
│   │   ├── rtt_cleaned/
│   │   ├── wlmds_cleaned/
│   │   ├── operational_cleaned/
│   │   └── reference_cleaned/
```

```
│   │
│   └── processed/
│       ├── rtt_provider_specialty_month.parquet
│       ├── wlmds_fairness.parquet
│       ├── operational_pressure.parquet
│       ├── reference_population.parquet
│       ├── modelling_dataset.parquet
│       └── priority_scores.parquet
│
├── src/
│   ├── 01_extract_data.py
│   ├── 02_clean_rtt.py
│   ├── 03_clean_wlmds.py
│   ├── 04_clean_operational.py
│   ├── 05_build_features.py
│   ├── 06_scoring_engine.py
│   ├── 07_simulation_engine.py
│   ├── 08_validation_checks.py
│   └── utils.py
│
├── app/
│   ├── streamlit_app.py
│   └── pages/
│       ├── 1_National_Overview.py
│       ├── 2_Provider_Specialty_Ranking.py
│       ├── 3_Fairness_Analysis.py
│       ├── 4_Operational_Pressure.py
│       ├── 5_Simulation_Comparison.py
│       └── 6_Explanation.py
│
├── outputs/
│   ├── charts/
│   ├── tables/
│   ├── rankings/
│   └── metrics/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering_test.ipynb
│   ├── 03_score_testing.ipynb
│   └── 04_app_result_review.ipynb
│
├── requirements.txt
└── README.md
```

## **5. Data sources and how each one is used Main waiting-list data** 

**Dataset Use** RTT full CSV 2025/26 Main waiting-list pressure Incomplete pathways Current backlog Incomplete pathways with DTA Patients waiting after decision to admit Admitted pathways Completed admitted treatment Non-admitted pathways Completed non-admitted treatment New RTT periods New demand entering waiting list 

## **Fairness data** 

## **Dataset** 

## **Use** 

WLMDS demographics geography Fairness by provider/geography WLMDS demographics specialty Fairness by specialty WLMDS demographics time series Demographic trends ONS age/sex population Population context ONS ethnicity Ethnicity population context IMD 2019 Deprivation context 

## **Operational pressure data** 

**Dataset Use** Diagnostics waiting times Diagnostic bottleneck A&E attendances and emergency admissions Emergency pressure Bed availability and occupancy KH03 Bed capacity pressure UEC sitrep beds Monthly/urgent bed pressure Operating theatres Theatre capacity Cancelled operations 2019 to 2026 Elective disruption pressure 

## **6. Main data structure** 

Your main modelling table should be: 

```
Provider × Specialty × Month
```

This is the safest structure because RTT data is monthly and provider-specialty based. 

## **Main table: modelling_dataset** 

## **Column** 

## **Meaning** 

month Reporting month quarter Reporting quarter provider_code NHS provider code provider_name NHS provider name treatment_function_code Specialty code treatment_function_name Specialty name incomplete_total Total incomplete RTT pathways breach_18w_count Number waiting over 18 weeks breach_52w_count Number waiting over 52 weeks dta_total Incomplete pathways with decision to admit new_rtt_total New RTT periods admitted_total Completed admitted pathways non_admitted_total Completed non-admitted pathways 

**Column Meaning** backlog_growth_rate Month-on-month backlog change throughput_rate Completed pathways compared with backlog diagnostic_over_6w_rate Diagnostic delay pressure ae_pressure_score Emergency care pressure bed_occupancy_rate Bed pressure theatre_pressure_score Theatre capacity pressure cancelled_ops_total Cancelled elective operations cancellation_pressure_score Elective disruption pressure fairness_age_score Age fairness risk fairness_sex_score Sex fairness risk fairness_ethnicity_score Ethnicity fairness risk fairness_deprivation_score Deprivation fairness risk missing_demographic_score Risk from missing demographic data waiting_pressure_score Waiting-list score fairness_risk_score Fairness score operational_pressure_score Operational score final_priority_score Final score priority_level Lower, moderate, high or critical 

## **7. Key data connection logic** 

The biggest challenge is joining different datasets together. 

## **Primary join keys** 

Use these where available: 

```
month
provider_code
treatment_function_code
```

## **Quarter-based datasets** 

Cancelled operations, bed KH03 and operating theatre files may be quarterly. 

For these, create a quarter field: 

```
April, May, June = Q1
July, August, September = Q2
October, November, December = Q3
January, February, March = Q4
```

Then join quarterly data to each month inside that quarter. 

Example: 

```
Q1 2025/26 cancelled operations
applies to April 2025, May 2025 and June 2025
```

## **Provider matching** 

Use `provider_code` as the main key. 

If some files only have provider names, create a provider lookup table: 

```
dim_provider
provider_code
provider_name
standard_provider_name
region
icb_code if available
```

Never rely only on provider name if code is available. 

## **Specialty matching** 

Use treatment function code where possible. 

Some operational data may not be specialty-specific. In that case, treat it as provider-level pressure and apply it to all provider-specialty rows for that provider-month. 

Example: 

```
Bed occupancy is provider-level
RTT is provider-specialty-level
So bed pressure joins by:
provider_code + month
```

## **8. Calculation logic** 

## **A. Waiting-list pressure** 

## **18-week breach count** 

```
18-week breach count =
sum of all incomplete waiting bands from 18 weeks upward
```

## **52-week long-wait count** 

```
52-week wait count =
sum of all incomplete waiting bands from 52 weeks upward
```

## **18-week breach rate** 

```
18-week breach rate =
```

```
breach_18w_count / incomplete_total
```

## **52-week long-wait rate** 

```
52-week long-wait rate =
breach_52w_count / incomplete_total
```

## **DTA pressure** 

```
DTA pressure =
dta_total / incomplete_total
```

## **Demand pressure** 

```
Demand pressure =
new_rtt_total / incomplete_total
```

## **Throughput rate** 

```
Throughput rate =
(admitted_total + non_admitted_total) / incomplete_total
```

## **Inverse throughput pressure** 

Because low throughput means high pressure: 

```
inverse throughput pressure =
1 - normalised throughput_rate
```

## **Backlog growth rate** 

```
backlog growth rate =
(current month incomplete_total - previous month incomplete_total)
/
previous month incomplete_total
```

## **Waiting pressure score** 

After normalising each component to 0 to 1: 

```
waiting_pressure_score =
0.30 × breach_18w_rate
+ 0.25 × breach_52w_rate
+ 0.15 × dta_pressure
+ 0.15 × backlog_growth_rate
+ 0.10 × demand_pressure
+ 0.05 × inverse_throughput_pressure
```

## **9. Fairness risk logic** 

Fairness is not about saying one group is more important than another. It is about identifying whether some groups are over-represented in long waits. 

Use WLMDS demographic data. 

## **Main fairness comparison** 

For each demographic group: 

```
share of all waits =
all waiting count for group / total waiting count
share of long waits =
long-wait count for group / total long-wait count
```

Then: 

```
fairness gap =
share of long waits - share of all waits
```

Example: 

```
If IMD 1-2 patients are 24% of all waiters
but 36% of 52-week waiters:
fairness gap = 36% - 24% = 12 percentage points
```

That means deprived groups are over-represented in the longest waits. 

## **Deprivation fairness score** 

```
deprivation_fairness_score =
maximum positive fairness gap across IMD groups
```

You can also group IMD like this: 

```
IMD 1-2 = most deprived
IMD 3-5 = deprived/middle
IMD 6-8 = less deprived
IMD 9-10 = least deprived
```

## **Ethnicity fairness score** 

```
ethnicity_fairness_score =
maximum positive fairness gap across ethnic groups
```

## **Age fairness score** 

```
age_fairness_score =
maximum positive fairness gap across age bands
```

## **Sex fairness score** 

```
sex_fairness_score =
absolute difference between male and female long-wait over-representation
```

## **Missing demographic score** 

This is important. 

If ethnicity or deprivation is missing for many records, fairness analysis becomes weaker. 

```
missing_demographic_score =
missing demographic count / total demographic count
```

## **Final fairness risk score** 

After normalising to 0 to 1: 

```
fairness_risk_score =
0.30 × deprivation_fairness_score
+ 0.25 × ethnicity_fairness_score
```

```
+ 0.20 × age_fairness_score
```

```
+ 0.15 × sex_fairness_score
+ 0.10 × missing_demographic_score
```

## **10. Population context logic** 

Use ONS and IMD carefully. 

Population data should not replace WLMDS fairness. It should provide context. 

## **Population over-representation** 

```
population_context_gap =
waiting_list_share_for_group - local_population_share_for_group
```

Example: 

```
If an ethnic group is 10% of the local population
but 18% of the waiting list:
```

```
population_context_gap = 8 percentage points
```

Important limitation: 

Provider catchment areas do not always match local authority boundaries. So this should be shown as **context** , not as final proof of unfairness. 

## **11. Operational pressure logic** 

Operational pressure explains why waiting-list pressure may be worse in some places. 

## **A. Diagnostic bottleneck score** 

```
diagnostic_over_6w_rate =
patients waiting over 6 weeks / total diagnostic waiting list
```

## Then normalise: 

```
diagnostic_bottleneck_score =
normalised diagnostic_over_6w_rate
```

## **B. A&E pressure score** 

Use provider-level A&E data. 

```
ae_4hour_breach_rate =
patients spending over 4 hours / total A&E attendances
emergency_admission_rate =
emergency admissions / total A&E attendances
ae_dta_delay_rate =
patients waiting long after decision to admit / total A&E attendances
```

Then: 

```
ae_pressure_score =
0.40 × ae_4hour_breach_rate
+ 0.30 × emergency_admission_rate
+ 0.30 × ae_dta_delay_rate
```

## **C. Bed pressure score** 

```
bed_occupancy_rate =
occupied_beds / available_beds
```

Then: 

```
bed_pressure_score =
normalised bed_occupancy_rate
```

## **D. Theatre pressure score** 

If theatre availability is available: 

```
theatre_capacity_rate =
available_theatres / maximum_available_theatres
```

Because lower capacity means higher pressure: 

```
theatre_pressure_score =
1 - normalised theatre_capacity_rate
```

## **E. Cancellation pressure score** 

If total elective operations are available: 

```
cancelled_operation_rate =
cancelled_operations / total_elective_operations
```

If total elective operations are not available: 

```
cancelled_operation_pressure =
normalised cancelled_operations
```

If 28-day breach is available: 

```
cancellation_28day_breach_rate =
patients_not_treated_within_28_days / cancelled_operations
```

Then: 

```
cancellation_pressure_score =
0.60 × cancelled_operation_rate
+ 0.40 × cancellation_28day_breach_rate
```

Or if rates cannot be calculated: 

```
cancellation_pressure_score =
0.60 × normalised_cancelled_operations
+ 0.40 × normalised_28day_breach_count
```

## **Final operational pressure score** 

```
operational_pressure_score =
0.25 × diagnostic_bottleneck_score
+ 0.25 × bed_pressure_score
+ 0.20 × ae_pressure_score
+ 0.15 × cancellation_pressure_score
+ 0.15 × theatre_pressure_score
```

## **12. Normalisation logic** 

Different metrics have different scales. You must normalise before scoring. 

Use min-max normalisation: 

```
normalised_value =
(value - minimum_value) / (maximum_value - minimum_value)
```

For outliers, use winsorisation before normalisation. 

Example: 

```
cap very extreme values at the 1st and 99th percentile
```

This stops one extreme provider from dominating the score. 

## **13. Final priority score** 

```
final_priority_score =
0.50 × waiting_pressure_score
+ 0.30 × fairness_risk_score
+ 0.20 × operational_pressure_score
```

Then scale to 100: 

```
priority_score_100 =
final_priority_score × 100
```

## **Priority levels** 

**Score Level** 0 to 39Lower priority 40 to 59Moderate priority 60 to 79High priority 80 to 100Critical priority 

## **14. Simulator strategies** 

The app should allow users to compare five strategies. 

## **Strategy 1: Waiting-time only** 

```
score =
0.60 × breach_18w_rate
+ 0.40 × breach_52w_rate
```

Purpose: 

Shows what happens when prioritisation is based only on waiting time. 

## **Strategy 2: Operational pressure** 

```
score =
0.50 × waiting_pressure_score
+ 0.50 × operational_pressure_score
```

Purpose: 

Shows what happens when capacity pressure is included. 

## **Strategy 3: Cancellation-aware** 

```
score =
```

```
0.45 × waiting_pressure_score
```

```
+ 0.35 × cancellation_pressure_score
```

```
+ 0.20 × bed_theatre_pressure_score
```

Purpose: 

Shows whether cancelled operations change the priority ranking. 

## **Strategy 4: Deprivation-weighted** 

```
score =
0.60 × waiting_pressure_score
+ 0.40 × deprivation_fairness_score
```

Purpose: 

Tests equity-sensitive prioritisation for deprived groups. 

## **Strategy 5: Full fairness-aware model** 

```
score =
0.50 × waiting_pressure_score
+ 0.30 × fairness_risk_score
+ 0.20 × operational_pressure_score
```

Purpose: 

This is your proposed model. 

## **15. App pages** 

## **Page 1: National overview** 

Show: 

```
total incomplete pathways
18-week breach rate
52-week long-wait rate
DTA pressure
new RTT demand
national cancellation trend
diagnostic bottleneck trend
bed occupancy trend
```

Charts: 

```
monthly waiting-list trend
top 10 pressured specialties
top 10 pressured providers
cancelled operations trend
```

## **Page 2: Provider-specialty ranking** 

Filters: 

```
month
provider
specialty
region
priority level
strategy
```

Show: 

```
provider name
specialty
waiting pressure score
fairness risk score
operational pressure score
final priority score
priority level
rank
```

## **Page 3: Fairness analysis** 

Filters: 

```
age
sex
ethnicity
deprivation
provider
specialty
waiting band
```

Show: 

```
share of all waits
share of long waits
fairness gap
most over-represented groups
missing demographic rate
```

## **Page 4: Operational pressure** 

Show: 

```
diagnostic bottleneck
A&E pressure
bed occupancy
theatre pressure
cancelled operations
28-day breach pressure
```

## **Page 5: Simulation comparison** 

Show: 

```
waiting-time-only rank
fairness-aware rank
cancellation-aware rank
rank movement
newly flagged critical areas
top 20 priority areas
```

## **Page 6: Explanation page** 

For each selected provider-specialty: 

```
Priority score: 84.7
Priority level: Critical
Main drivers:
```

`1. High 52-week long-wait rate` 

`2. High DTA pressure` 

`3. High cancellation pressure` 

`4. High bed occupancy` 

`5. Deprived groups over-represented in long waits` 

## **16. Metrics to evaluate the simulator** 

You need app metrics, not paper metrics yet. 

## **A. Ranking shift metric** 

Measures how much the fairness-aware model changes the ranking. 

```
rank_shift =
waiting_time_only_rank - fairness_aware_rank
```

Positive rank shift means the area moves up when fairness is included. 

## **B. Top-k overlap** 

Compare top 20 providers under different strategies. 

```
top_k_overlap =
number of shared providers in both top 20 lists / 20
```

Low overlap means fairness-aware scoring changes prioritisation meaningfully. 

## **C. Fairness lift** 

Measures whether fairness-aware prioritisation identifies more high-risk demographic areas. 

```
fairness_lift =
average fairness risk in top 20 fairness-aware list
-
average fairness risk in top 20 waiting-time-only list
```

## **D. Operational lift** 

```
operational_lift =
average operational pressure in top 20 operational model
-
average operational pressure in top 20 waiting-time-only model
```

## **E. Cancellation impact** 

```
cancellation_impact =
average cancellation pressure in top 20 cancellation-aware list
-
average cancellation pressure in top 20 waiting-time-only list
```

## **F. Sensitivity stability** 

Test whether priority areas remain high when weights change. 

Example weight settings: 

```
Main model:
50 waiting, 30 fairness, 20 operational
Sensitivity A:
60 waiting, 25 fairness, 15 operational
Sensitivity B:
40 waiting, 40 fairness, 20 operational
Sensitivity C:
45 waiting, 25 fairness, 30 operational
```

Metric: 

```
stability_rate =
number of providers staying in top 20 across scenarios / 20
```

## **17. Validation checks** 

Before trusting the app, build validation checks. 

## **Data checks** 

```
No negative counts
No impossible percentages above 100%
Provider codes are consistent
Month fields are valid
Quarter mapping is correct
Totals are not double counted
Missing values are documented
```

## **Score checks** 

```
All normalised scores must be between 0 and 1
Final priority score must be between 0 and 100
Priority levels must match score ranges
No provider should appear twice for same month and specialty
```

## **Logic checks** 

```
High 52-week waits should increase priority
High cancellation pressure should increase operational pressure
High missing demographic rate should increase fairness uncertainty
Low throughput should increase waiting pressure
```

## **18. SQL Server optional schema** 

If you use SQL Server later, use this structure. 

## **Dimension tables** 

```
dim_provider
provider_key
provider_code
provider_name
region
icb_code
dim_specialty
specialty_key
treatment_function_code
treatment_function_name
dim_time
time_key
month
quarter
financial_year
dim_demographic
demographic_key
demographic_type
demographic_group
```

## **Fact tables** 

```
fact_rtt_waits
time_key
provider_key
specialty_key
incomplete_total
breach_18w_count
breach_52w_count
dta_total
new_rtt_total
```

```
admitted_total
non_admitted_total
fact_wlmds_fairness
time_key
provider_key
specialty_key
demographic_key
all_wait_count
long_wait_count
fairness_gap
fact_operational_pressure
time_key
provider_key
diagnostic_bottleneck_score
ae_pressure_score
bed_pressure_score
theatre_pressure_score
cancellation_pressure_score
fact_priority_scores
time_key
provider_key
specialty_key
waiting_pressure_score
fairness_risk_score
operational_pressure_score
final_priority_score
priority_level
strategy_name
```

## **19. Build sequence** 

## **Step 1: Set up project** 

Create folders. 

Install packages: 

```
pandas
numpy
openpyxl
pyarrow
streamlit
plotly
scikit-learn
```

## **Step 2: Extract and catalogue files** 

Create: 

```
data_catalogue.csv
```

Columns: 

```
file_name
folder
data_source
period
file_type
status
notes
```

## **Step 3: Clean RTT data** 

Output: 

```
rtt_provider_specialty_month.parquet
```

## **Step 4: Clean WLMDS data** 

Output: 

```
wlmds_fairness.parquet
```

## **Step 5: Clean operational data** 

Outputs: 

```
diagnostics_pressure.parquet
ae_pressure.parquet
bed_pressure.parquet
theatre_pressure.parquet
cancelled_operations_pressure.parquet
```

## **Step 6: Build modelling dataset** 

Join everything into: 

```
modelling_dataset.parquet
```

## **Step 7: Build scoring engine** 

Output: 

```
priority_scores.parquet
```

## **Step 8: Build simulation engine** 

Output: 

```
strategy_comparison.parquet
```

## **Step 9: Build Streamlit app** 

Start with one page first: 

```
Provider-specialty ranking
```

Then add: 

```
fairness page
operational page
simulation page
explanation page
```

## **Step 10: Export results** 

Save: 

```
top_20_priority_areas.csv
strategy_comparison.csv
fairness_lift_results.csv
sensitivity_analysis.csv
charts for later paper
```

## **20. Final success criteria** 

You know the prototype is complete when it can do these things: 

```
Load cleaned NHS public data locally
Create provider-specialty-month records
Calculate waiting pressure score
Calculate fairness risk score
Calculate operational pressure score
Include cancelled operations as a pressure signal
Generate final priority score
Compare five prioritisation strategies
Show rank movement caused by fairness and cancellation pressure
Explain why each provider-specialty area is high priority
Export charts and tables for later journal writing
```

## **21. Recommended first build** 

Do not build everything at once. 

Build in this order: 

`1. RTT waiting pressure only` 

`2. Add WLMDS fairness risk` 

`3. Add diagnostics, A&E and beds` 

`4. Add operating theatres and cancelled operations` 

`5. Add final priority score` 

`6. Add simulation comparison` 

`7. Build Streamlit app` 

`8. Export metrics and results` 

## **Final direction** 

The project should be built as a **local simulator** , not a cloud product. 

Use: 

```
Local folders
Parquet processed files
Python scoring engine
Streamlit app
Optional SQL Server later
```

The strongest version of the simulator is: 

```
FairQueue Simulator:
A local public-data app that ranks NHS provider-specialty areas using
waiting-list pressure, fairness risk, operational pressure and cancellation
disruption.
```

That is the full route from architecture to calculation to simulator output. 

