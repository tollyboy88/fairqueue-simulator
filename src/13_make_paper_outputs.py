"""Generate the three figures and two tables used in the submission."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import OUTPUTS, PROCESSED  # noqa: E402

FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"


def save_figure(figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURES / f"{name}.png", dpi=220, bbox_inches="tight")
    figure.savefig(
        FIGURES / f"{name}.tiff",
        dpi=300,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(figure)


def workflow_figure() -> None:
    figure, axis = plt.subplots(figsize=(12, 3.7))
    axis.axis("off")
    boxes = [
        (0.02, "Dated public data\nRTT and operations"),
        (0.27, "Future-outcome forecast\n52-week breach rate at t+3"),
        (0.52, "Strict temporal test\nUnseen future months"),
        (0.77, "Equity-constrained top-K\nExplicit representation floor"),
    ]
    for x, text in boxes:
        axis.text(
            x,
            0.52,
            text,
            transform=axis.transAxes,
            ha="left",
            va="center",
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#eef4fb", edgecolor="#26547c"),
        )
    for x in (0.22, 0.47, 0.72):
        axis.annotate(
            "",
            xy=(x + 0.04, 0.52),
            xytext=(x, 0.52),
            xycoords="axes fraction",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.8),
        )
    axis.text(
        0.5,
        0.12,
        "Demographic disparity indicators enter only the policy layer, never model training.",
        transform=axis.transAxes,
        ha="center",
        fontsize=10,
        color="#444444",
    )
    axis.set_title("FairQueue 2.0 forecasting and decision-support workflow", fontsize=14, pad=14)
    save_figure(figure, "Figure1_workflow")


def temporal_figure(selected_model: str) -> None:
    monthly = pd.read_csv(OUTPUTS / "metrics" / "monthly_test_metrics.csv")
    monthly = monthly[monthly.model.isin(["Persistence", selected_model])]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    colors = {"Persistence": "#8d99ae", selected_model: "#26547c"}
    for model, group in monthly.groupby("model"):
        axes[0].plot(
            group.target_month, 100 * group.mae, marker="o", label=model, color=colors[model]
        )
        axes[1].plot(
            group.target_month, group.ndcg_at_20, marker="o", label=model, color=colors[model]
        )
    axes[0].set_ylabel("MAE in 52-week breach rate (percentage points)")
    axes[1].set_ylabel("NDCG@20")
    for axis in axes:
        axis.tick_params(axis="x", rotation=45)
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    figure.suptitle("Performance across the nine held-out target months")
    figure.tight_layout()
    save_figure(figure, "Figure2_temporal_performance")


def tradeoff_figure() -> None:
    tradeoff = pd.read_csv(OUTPUTS / "metrics" / "equity_utility_tradeoff.csv")
    curve = tradeoff[tradeoff.strategy == "Equity-constrained forecast"].copy()
    figure, axis = plt.subplots(figsize=(7.5, 4.8))
    axis.plot(
        100 * curve.high_equity_need_share,
        100 * curve.observed_pressure_mean,
        marker="o",
        color="#2a9d8f",
        linewidth=2,
    )
    labelled = curve[curve.minimum_high_need_share.isin([0.0, 0.4, 0.5])]
    for _, row in labelled.iterrows():
        label = (
            "0–30% floors"
            if row.minimum_high_need_share == 0.0
            else f"{int(100 * row.minimum_high_need_share)}% floor"
        )
        axis.annotate(
            label,
            (100 * row.high_equity_need_share, 100 * row.observed_pressure_mean),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8,
        )
    axis.set_xlabel("Selected areas from high-equity-need providers (%)")
    axis.set_ylabel("Mean subsequently observed 52-week breach rate (%)")
    axis.set_title("Observed utility-equity trade-off for K = 20")
    axis.grid(alpha=0.25)
    figure.tight_layout()
    save_figure(figure, "Figure3_equity_utility_tradeoff")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    selected = json.loads(
        (OUTPUTS / "metrics" / "selected_model.json").read_text(encoding="utf-8")
    )["selected_model"]
    metrics = pd.read_csv(OUTPUTS / "metrics" / "test_model_metrics.csv")
    intervals = pd.read_csv(OUTPUTS / "metrics" / "bootstrap_confidence_intervals.csv")
    compact = metrics[
        [
            "model",
            "mae",
            "rmse",
            "r2",
            "spearman",
            "recall_at_20",
            "ndcg_at_20",
        ]
    ].copy()
    compact.to_csv(TABLES / "Table1_test_model_performance.csv", index=False)
    pd.read_csv(OUTPUTS / "metrics" / "equity_utility_tradeoff.csv").to_csv(
        TABLES / "Table2_equity_utility_tradeoff.csv", index=False
    )
    data = pd.read_parquet(PROCESSED / "forecast_dataset.parquet")
    summary = {
        "selected_model": selected,
        "rows": int(len(data)),
        "providers": int(data.provider_code.nunique()),
        "specialties": int(data.treatment_function_code.nunique()),
        "feature_month_start": str(data.feature_date.min().date()),
        "feature_month_end": str(data.feature_date.max().date()),
        "test_rows": int((data.split == "test").sum()),
        "test_target_months": int(data.loc[data.split == "test", "target_date"].nunique()),
        "test_metrics": metrics[metrics.model == selected].iloc[0].to_dict(),
        "persistence_metrics": metrics[metrics.model == "Persistence"].iloc[0].to_dict(),
        "selected_model_intervals": intervals[intervals.model == selected].to_dict("records"),
    }
    (OUTPUTS / "metrics" / "paper_results.json").write_text(
        json.dumps(summary, indent=2, default=float), encoding="utf-8"
    )
    workflow_figure()
    temporal_figure(selected)
    tradeoff_figure()
    print("Generated three figures, two tables, and paper_results.json")


if __name__ == "__main__":
    main()
