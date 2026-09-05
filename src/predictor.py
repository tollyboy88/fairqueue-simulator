"""Forecasting utilities for FairQueue 2.0.

The target is an observed future 52-week breach rate. Equity variables are
deliberately absent from every feature list.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    ndcg_score,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
MODELS = ROOT / "models"
MODEL_PATH = MODELS / "fairqueue_forecaster.joblib"
TARGET = "target_breach_52w_rate"
CATEGORICAL = ["treatment_function_code"]

RTT_FEATURES = [
    "breach_18w_rate",
    "breach_52w_rate",
    "dta_rate",
    "demand_rate",
    "throughput_rate",
    "demand_throughput_ratio",
    "backlog_growth_rate",
    "breach_18w_rate_lag1",
    "breach_18w_rate_lag3",
    "breach_52w_rate_lag1",
    "breach_52w_rate_lag2",
    "breach_52w_rate_lag3",
    "breach_52w_mom_change",
    "breach_52w_trend3",
    "breach_52w_acceleration",
    "breach_52w_roll3",
    "breach_52w_roll6",
    "log_incomplete_total",
    "month_sin",
    "month_cos",
]
DIAGNOSTIC_FEATURES = RTT_FEATURES + ["diagnostic_over_6w_rate"]
FULL_FEATURES = DIAGNOSTIC_FEATURES + [
    "bed_occupancy_rate",
    "log_cancelled_operations",
    "cancel_28day_breach_rate",
]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: object
    scale: bool = False


def model_specs(random_state: int = 42) -> list[ModelSpec]:
    specs = [
        ModelSpec(
            "Elastic Net",
            ElasticNet(alpha=0.001, l1_ratio=0.25, max_iter=20_000, random_state=random_state),
            True,
        ),
        ModelSpec(
            "Random Forest",
            RandomForestRegressor(
                n_estimators=60,
                max_depth=12,
                min_samples_leaf=20,
                max_features=0.6,
                n_jobs=1,
                random_state=random_state,
            ),
        ),
        ModelSpec(
            "Histogram Gradient Boosting",
            HistGradientBoostingRegressor(
                max_iter=250,
                learning_rate=0.05,
                max_leaf_nodes=31,
                min_samples_leaf=25,
                l2_regularization=1.0,
                random_state=random_state,
            ),
        ),
    ]
    try:
        from xgboost import XGBRegressor

        specs.append(
            ModelSpec(
                "XGBoost",
                XGBRegressor(
                    n_estimators=300,
                    max_depth=5,
                    learning_rate=0.05,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    objective="reg:squarederror",
                    n_jobs=1,
                    random_state=random_state,
                ),
            )
        )
    except ImportError:
        pass
    return specs


def build_pipeline(spec: ModelSpec, numeric_features: list[str]) -> Pipeline:
    numeric_steps = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
    if spec.scale:
        numeric_steps.append(("scale", StandardScaler()))
    preprocess = ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), numeric_features),
            (
                "specialty",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL,
            ),
        ],
        remainder="drop",
        sparse_threshold=0,
    )
    return Pipeline([("preprocess", preprocess), ("model", spec.estimator)])


def predictor_columns(features: list[str]) -> list[str]:
    return [*features, *CATEGORICAL]


def point_metrics(y_true, y_pred) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    rho = spearmanr(true, pred, nan_policy="omit").statistic
    return {
        "mae": float(mean_absolute_error(true, pred)),
        "rmse": float(math.sqrt(mean_squared_error(true, pred))),
        "r2": float(r2_score(true, pred)),
        "spearman": float(rho),
    }


def ranking_metrics(frame: pd.DataFrame, prediction: str, ks=(10, 20, 50)) -> dict[str, float]:
    rows = []
    for _, month in frame.groupby("target_date"):
        month = month.dropna(subset=[TARGET, prediction])
        if len(month) < 2:
            continue
        values = {}
        for requested_k in ks:
            k = min(requested_k, len(month))
            actual = set(month.nlargest(k, TARGET).index)
            predicted = set(month.nlargest(k, prediction).index)
            overlap = len(actual & predicted)
            values[f"precision_at_{requested_k}"] = overlap / k
            values[f"recall_at_{requested_k}"] = overlap / k
            values[f"ndcg_at_{requested_k}"] = float(
                ndcg_score(
                    month[[TARGET]].to_numpy().T,
                    month[[prediction]].to_numpy().T,
                    k=k,
                )
            )
        rows.append(values)
    return pd.DataFrame(rows).mean().to_dict() if rows else {}


def evaluate(frame: pd.DataFrame, prediction: str) -> dict[str, float]:
    return {
        **point_metrics(frame[TARGET], frame[prediction]),
        **ranking_metrics(frame, prediction),
    }


def baseline_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["Persistence"] = result["breach_52w_rate"]
    result["Three-month mean"] = result["breach_52w_roll3"]
    return result


def feature_importance(
    model: Pipeline, frame: pd.DataFrame, features: list[str], random_state: int = 42
) -> pd.DataFrame:
    columns = predictor_columns(features)
    sample = frame.sample(min(4_000, len(frame)), random_state=random_state)
    importance = permutation_importance(
        model,
        sample[columns],
        sample[TARGET],
        scoring="neg_mean_absolute_error",
        n_repeats=5,
        random_state=random_state,
        n_jobs=1,
    )
    return pd.DataFrame(
        {
            "feature": columns,
            "importance_mean": importance.importances_mean,
            "importance_sd": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)


def save_bundle(model: Pipeline, features: list[str], selected_name: str) -> None:
    MODELS.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "numeric_features": features,
            "categorical_features": CATEGORICAL,
            "target": TARGET,
            "selected_model": selected_name,
            "horizon_months": 3,
        },
        MODEL_PATH,
    )


def load_model() -> dict:
    return joblib.load(MODEL_PATH)
