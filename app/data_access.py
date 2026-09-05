"""Cached data access for the FairQueue 2.0 Streamlit explorer."""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
METRICS = ROOT / "outputs" / "metrics"


@st.cache_data(show_spinner=False)
def predictions() -> pd.DataFrame:
    frame = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    frame["target_month"] = pd.to_datetime(frame["target_date"]).dt.strftime("%Y-%m")
    return frame


@st.cache_data(show_spinner=False)
def selections() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "equity_constrained_selections.parquet")


@st.cache_data(show_spinner=False)
def equity_indicators() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "equity_indicators.parquet")


@st.cache_data(show_spinner=False)
def metric(name: str) -> pd.DataFrame:
    return pd.read_csv(METRICS / name)
