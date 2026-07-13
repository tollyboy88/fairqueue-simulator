"""Shared data loaders for the FairQueue Streamlit app (cached)."""
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INTERIM = ROOT / "data" / "interim"
OUTPUTS = ROOT / "outputs"

STRATEGY_LABELS = {
    "waiting_time_only": "Waiting-time only",
    "operational": "Operational pressure",
    "cancellation_aware": "Cancellation-aware",
    "deprivation_weighted": "Deprivation-weighted",
    "full_fairness_aware": "Full fairness-aware (proposed)",
}
LEVEL_COLOURS = {"Critical": "#d00000", "High": "#f48c06",
                 "Moderate": "#ffd166", "Lower": "#90be6d"}


@st.cache_data(show_spinner=False)
def scores() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "priority_scores.parquet")


@st.cache_data(show_spinner=False)
def strategies() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "strategy_comparison.parquet")


@st.cache_data(show_spinner=False)
def modelling() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "modelling_dataset.parquet")


@st.cache_data(show_spinner=False)
def rtt() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "rtt_provider_specialty_month.parquet")


@st.cache_data(show_spinner=False)
def operational() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "operational_pressure.parquet")


@st.cache_data(show_spinner=False)
def fairness_detail() -> pd.DataFrame:
    p = INTERIM / "wlmds_cleaned" / "wlmds_fairness_detail.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def metric_csv(name: str) -> pd.DataFrame:
    p = OUTPUTS / "metrics" / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def months(df) -> list:
    return sorted(df["month"].unique())
