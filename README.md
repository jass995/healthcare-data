# 🏥 Healthcare Admissions Dashboard

An interactive Streamlit dashboard exploring 55,500 hospital admissions (May 2019 – May 2024): volumes, billing, patient demographics and clinical outcomes.

## Features
- **Sidebar filters**: date range, condition, admission type, insurer, gender, age
- **KPIs**: admissions, total/avg billing, avg length of stay, % abnormal results
- **Tabs**: Overview · Billing · Patients · Clinical · Data (with CSV download)
- **Cleaning**: normalises name casing, optionally removes duplicate rows and negative billing amounts

## Run locally
```bash
git clone https://github.com/<your-username>/healthcare-dashboard.git
cd healthcare-dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free on Streamlit Community Cloud
1. Push this repo to GitHub
2. Go to https://share.streamlit.io → **New app**
3. Select the repo, branch `main`, main file `app.py` → **Deploy**
4. Add the live URL to this README

## Data notes
- 534 exact duplicate rows (removed by default)
- 108 negative billing amounts (toggle in sidebar)
- Length of stay is derived from admission and discharge dates
