# How to run FairQueue in VS Code

## First time only
1. **Open the folder** — File → Open Folder → select this project folder.
2. **Open a terminal** — Terminal → New Terminal (or `` Ctrl+` ``).
3. **Install the Python extension** (optional but recommended) — Extensions panel → search "Python" → Install. Then `Ctrl+Shift+P` → "Python: Select Interpreter".
4. **Install packages:**
   ```powershell
   python -m pip install -r requirements.txt
   ```
   If `python` isn't recognised, use `py -m pip install -r requirements.txt`.

## Launch the interactive app (8 pages)
```powershell
python -m streamlit run app/streamlit_app.py
```
- Opens your browser at http://localhost:8501
- Move between pages with the left sidebar
- Stop the server with `Ctrl+C` in the terminal

Pages: National Overview · Provider-Specialty Ranking · Fairness Analysis ·
Operational Pressure · Simulation Comparison · Explanation ·
**Data Preparation** (upload raw files → auto clean & join) ·
**Predict & Explain** (ML priority model + explainable-AI report + fairness audit).

The two new pages accept **Excel / CSV** data uploads and an optional **Word (.docx)**
rubric of feature weights. The prediction model is pre-trained
(`models/fairqueue_model.joblib`); it retrains automatically if that file is missing.

> Use `python -m streamlit ...` (not just `streamlit run`) to avoid the
> "streamlit is not recognized" PATH error on Windows.

## View without a server
Double-click **`outputs/FairQueue_Dashboard.html`** — opens in any browser, no install.

## Rebuild all data + outputs from scratch
```powershell
python run_all.py
```
Re-runs the whole pipeline (RTT → fairness → operational → scoring → simulation →
charts → dashboard → notebook). Heavy Excel reads are cached, so re-runs are fast.

## Optional: use a virtual environment (keeps packages isolated)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```
If PowerShell blocks activation, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Troubleshooting
- **"streamlit is not recognized"** → use `python -m streamlit run app/streamlit_app.py`.
- **"No module named …"** → re-run `python -m pip install -r requirements.txt` with the interpreter VS Code shows in the bottom bar.
- **Port already in use** → `python -m streamlit run app/streamlit_app.py --server.port 8502`.
- **App loads but says data not found** → run `python run_all.py` first.
