# Nursing Staff Workload Balance Analyzer — NurseBalance Local

A 100% local Streamlit dashboard that identifies uneven nursing workload, overtime pressure, skill-mix gaps, and ward-level staffing pressure for hospital planning.

## Core capabilities
- Workload balance matrix
- Overtime and schedule pressure analysis
- Skill-mix gap analysis
- Ward pressure ranking with Low / Moderate / High / Critical classification
- Individual workload fairness review
- What-if staffing scenario lab
- CSV reports and exports
- Local SVG visual assets; no external APIs or cloud inference

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest tests/ -q
streamlit run app.py
```

## Data
Upload CSV files only from the sidebar. Sample files are included in `data/`.

## Responsible use
This tool is for workforce planning and workload review. It must not be used as a substitute for clinical judgment, nurse-manager oversight, HR policy, safe-staffing rules, or emergency staffing procedures.
