"""Run the complete FairQueue 2.0 research pipeline."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "01_download_longitudinal_data.py",
    "02_clean_rtt.py",
    "03_clean_wlmds_longitudinal.py",
    "04_clean_operational.py",
    "05_build_longitudinal_features.py",
    "06_build_future_targets.py",
    "07_train_forecasting_models.py",
    "08_temporal_evaluation.py",
    "09_build_equity_indicators.py",
    "10_equity_constrained_ranking.py",
    "11_ablation_analysis.py",
    "12_robustness_analysis.py",
    "14_build_dashboard.py",
]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--skip-download", action="store_true",
    help="Reuse files already listed in data/source_manifest.csv.",
)
args = parser.parse_args()
steps = STEPS[1:] if args.skip_download else STEPS

for s in steps:
    print(f"\n=== {s} ===")
    r = subprocess.run([sys.executable, str(ROOT / "src" / s)])
    if r.returncode != 0:
        print(f"!! {s} failed (exit {r.returncode}); stopping.")
        sys.exit(r.returncode)
print("\nPipeline complete. View results:")
print("  - outputs/FairQueue_2_Dashboard.html")
print("  - outputs/metrics/test_model_metrics.csv")
print("  - outputs/metrics/equity_pressure_capture_frontier.csv")
print("  - outputs/metrics/paired_bootstrap_differences.csv")
print("  - outputs/metrics/provider_cap_sensitivity.csv")
print("  - streamlit run app/streamlit_app.py")
