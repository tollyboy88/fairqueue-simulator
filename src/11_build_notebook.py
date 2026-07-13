"""Generate notebooks/04_app_result_review.ipynb (results walkthrough)."""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = Path(__file__).resolve().parents[1]
nb = new_notebook()
c = []

c.append(new_markdown_cell(
    "# FairQueue Simulator — results review\n\n"
    "Walkthrough of the processed outputs: waiting-list pressure, fairness risk, "
    "operational pressure, the final priority score, and the five-strategy simulation.\n\n"
    "Run top-to-bottom after the pipeline (`src/02`–`src/07`) has produced the parquet files."))

c.append(new_code_cell(
    "import pandas as pd, plotly.express as px\n"
    "from pathlib import Path\n"
    "P = Path.cwd().parent / 'data' / 'processed' if (Path.cwd().name=='notebooks') else Path('data/processed')\n"
    "scores = pd.read_parquet(P/'priority_scores.parquet')\n"
    "rtt = pd.read_parquet(P/'rtt_provider_specialty_month.parquet')\n"
    "strat = pd.read_parquet(P/'strategy_comparison.parquet')\n"
    "latest = scores.month.max()\n"
    "print('rows:', len(scores), '| months:', scores.month.nunique(), '| latest:', latest)"))

c.append(new_markdown_cell("## 1. National waiting-list trend"))
c.append(new_code_cell(
    "g = rtt.groupby('month').agg(incomplete=('incomplete_total','sum'),\n"
    "    b18=('breach_18w_count','sum'), b52=('breach_52w_count','sum'))\n"
    "g['pct_within_18w'] = (100*(1-g.b18/g.incomplete)).round(1)\n"
    "g"))

c.append(new_markdown_cell("## 2. Top priority areas (full fairness-aware model)"))
c.append(new_code_cell(
    "cols=['provider_name','treatment_function_name','waiting_pressure_score',\n"
    "      'fairness_risk_score','operational_pressure_score','priority_score_100','priority_level']\n"
    "scores[scores.month==latest].nlargest(15,'priority_score_100')[cols].round(2)"))

c.append(new_markdown_cell(
    "## 3. Does fairness change prioritisation?\n"
    "Compare the top-20 of each strategy with the waiting-time-only baseline."))
c.append(new_code_cell(
    "k=20\n"
    "g=strat[strat.month==latest]\n"
    "base=set(g.nsmallest(k,'rank_waiting_time_only')[['provider_code','treatment_function_code']].apply(tuple,axis=1))\n"
    "for s in ['operational','cancellation_aware','deprivation_weighted','full_fairness_aware']:\n"
    "    cur=set(g.nsmallest(k,f'rank_{s}')[['provider_code','treatment_function_code']].apply(tuple,axis=1))\n"
    "    print(f'{s:22s} top-20 overlap with waiting-only: {len(base&cur)/k:.0%}')"))

c.append(new_markdown_cell("## 4. Biggest movers under the fairness-aware model"))
c.append(new_code_cell(
    "m=strat[strat.month==latest].nlargest(12,'shift_full_fairness_aware')\n"
    "m[['provider_name','treatment_function_name','rank_waiting_time_only',\n"
    "   'rank_full_fairness_aware','shift_full_fairness_aware']]"))

c.append(new_markdown_cell("## 5. Score distribution by priority component"))
c.append(new_code_cell(
    "px.scatter(scores[scores.month==latest], x='waiting_pressure_score', y='fairness_risk_score',\n"
    "    size='priority_score_100', color='operational_pressure_score', hover_name='provider_name',\n"
    "    title='Waiting vs fairness (size = priority, colour = operational)')"))

c.append(new_markdown_cell(
    "## Notes for the paper\n"
    "- Low top-20 overlap (~25% for the full model, 0% deprivation-weighted) = fairness-aware "
    "scoring materially changes which areas are flagged.\n"
    "- See `outputs/metrics/` for fairness/operational/cancellation lifts and the sensitivity analysis.\n"
    "- All scores are transparent weighted sums of min-max-normalised public NHS metrics — no black box."))

nb["cells"] = c
out = ROOT / "notebooks" / "04_app_result_review.ipynb"
nbf.write(nb, str(out))
print("Wrote", out)
