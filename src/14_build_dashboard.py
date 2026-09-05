"""Build a self-contained HTML dashboard for FairQueue 2.0 results."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

from utils import OUTPUTS, PROCESSED


def main() -> None:
    metrics_dir = OUTPUTS / "metrics"
    selected = json.loads((metrics_dir / "selected_model.json").read_text(encoding="utf-8"))[
        "selected_model"
    ]
    predictions = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    tradeoff = pd.read_csv(metrics_dir / "equity_utility_tradeoff.csv")
    model_metrics = pd.read_csv(metrics_dir / "test_model_metrics.csv")
    monthly = pd.read_csv(metrics_dir / "monthly_test_metrics.csv")
    latest = predictions[predictions.target_date == predictions.target_date.max()].copy()

    temporal = px.line(
        monthly[monthly.model.isin(["Persistence", selected])],
        x="target_month",
        y="mae",
        color="model",
        markers=True,
        title="Held-out monthly forecast error",
        labels={"mae": "MAE in 52-week breach rate", "target_month": "Outcome month"},
    )
    curve = px.line(
        tradeoff[tradeoff.strategy == "Equity-constrained forecast"],
        x="high_equity_need_share",
        y="observed_pressure_mean",
        markers=True,
        text="minimum_high_need_share",
        title="Observed utility-equity trade-off at K=20",
    )
    latest_rank = latest.nlargest(30, selected)[
        [
            "provider_name",
            "treatment_function_name",
            "breach_52w_rate",
            selected,
            "target_breach_52w_rate",
        ]
    ].copy()
    latest_rank.columns = [
        "Provider",
        "Specialty",
        "Current 52-week rate",
        "Predicted future rate",
        "Observed future rate",
    ]
    figure_html = temporal.to_html(full_html=False, include_plotlyjs="inline")
    curve_html = curve.to_html(full_html=False, include_plotlyjs=False)
    table_html = latest_rank.to_html(index=False, classes="results", float_format=lambda x: f"{x:.3f}")
    metrics_html = model_metrics.round(4).to_html(index=False, classes="results")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FairQueue 2.0</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fb;color:#1d2733}}
header{{padding:24px 34px;background:#173f5f;color:white}}
main{{max-width:1180px;margin:auto;padding:24px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.card{{background:white;padding:18px;border-radius:10px;box-shadow:0 1px 5px #ccd4dd}}
.results{{border-collapse:collapse;width:100%;font-size:13px}}
.results th{{background:#173f5f;color:white;padding:8px;text-align:left}}
.results td{{padding:7px;border-bottom:1px solid #dde3e8}}
h2{{color:#173f5f}} .note{{color:#53606b}}
</style></head><body>
<header><h1>FairQueue 2.0</h1>
<p>Temporally validated forecasting and equity-constrained elective-care prioritisation</p></header>
<main>
<p class="note">The forecast target is the observed provider-specialty 52-week breach rate three months later.
Demographic disparities are used only in the constrained decision layer.</p>
<div class="grid"><div class="card">{figure_html}</div><div class="card">{curve_html}</div></div>
<div class="card"><h2>Final temporal test metrics</h2>{metrics_html}</div>
<div class="card"><h2>Latest held-out forecasts and outcomes</h2>{table_html}</div>
</main></body></html>"""
    output = OUTPUTS / "FairQueue_2_Dashboard.html"
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    output.write_text(html, encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
