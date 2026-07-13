"""
12_train_model.py
------------------
Train and persist the fairness-aware priority model, then print metrics, global
feature importance and a fairness/bias audit. Saves:
    models/fairqueue_model.joblib
    outputs/metrics/model_metrics.json
    outputs/metrics/model_feature_importance.csv
"""
from pathlib import Path
import sys, json
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
import predictor as P  # noqa
from utils import PROCESSED, OUTPUTS  # noqa


def main():
    bundle = P.train_and_save()
    print("Model metrics:", bundle["metrics"])

    imp = (pd.Series(bundle["importances"]).rename("importance")
           .rename_axis("feature").reset_index()
           .assign(label=lambda d: d.feature.map(P.FEATURE_LABELS))
           .sort_values("importance", ascending=False))
    (OUTPUTS / "metrics").mkdir(parents=True, exist_ok=True)
    imp.to_csv(OUTPUTS / "metrics" / "model_feature_importance.csv", index=False)
    (OUTPUTS / "metrics" / "model_metrics.json").write_text(json.dumps(bundle["metrics"], indent=2))
    print("\nTop feature importances:")
    print(imp[["label", "importance"]].head(8).to_string(index=False))

    # fairness audit on the full scored dataset
    df = pd.read_parquet(PROCESSED / "modelling_dataset.parquet")
    feats = df[P.FEATURES].copy()
    pred = P.predict(bundle, feats)
    audit = P.fairness_audit(pred)
    print("\nFairness audit — corr(fairness gap, predicted priority):")
    for k, v in audit["correlations"].items():
        print(f"  {k:32s} {v:+.3f}")
    if "priority_by_deprivation_tercile" in audit:
        print("Mean predicted priority by deprivation tercile:",
              audit["priority_by_deprivation_tercile"])
        print("Bias flag (higher-deprivation under-prioritised)?", audit.get("bias_flag"))


if __name__ == "__main__":
    main()
