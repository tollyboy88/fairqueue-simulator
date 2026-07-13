"""
run_all.py — run the full FairQueue pipeline end to end.
Usage:  python run_all.py
(RTT and operational steps cache per-month/per-source, so re-runs are fast.)
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "01_extract_data.py", "02_clean_rtt.py", "03_clean_wlmds.py",
    "04_clean_operational.py", "05_build_features.py", "06_scoring_engine.py",
    "07_simulation_engine.py", "08_validation_checks.py", "09_make_charts.py",
    "10_build_static_dashboard.py", "11_build_notebook.py", "12_train_model.py",
]
for s in STEPS:
    print(f"\n=== {s} ===")
    r = subprocess.run([sys.executable, str(ROOT / "src" / s)])
    if r.returncode != 0:
        print(f"!! {s} failed (exit {r.returncode}); stopping.")
        sys.exit(r.returncode)
print("\nPipeline complete. View results:")
print("  • outputs/FairQueue_Dashboard.html   (open in a browser)")
print("  • streamlit run app/streamlit_app.py  (interactive 6-page app)")
