from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "healthcare_dataset.csv"

st.set_page_config(page_title="Healthcare Dashboard", page_icon="🏥", layout="wide")


# ---------------------------------------------------------------- data
@st.cache_data
def load_data(drop_duplicates: bool = True) -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["Date of Admission", "Discharge Date"])
    # Names/doctors have random casing ("DAvId muNoZ") -> normalise
    df["Name"] = df["Name"].str.strip().str.title()
    if drop_duplicates:
        df = df.drop_duplicates()
    df["Length of Stay"] = (df["Discharge Date"] - df["Date of Admission"]).dt.days
    df["Admission Month"] = df["Date of Admission"].dt.to_period("M").dt.to_timestamp()
    df["Age Group"] = pd.cut(
        df["Age"],
        bins=[0, 17, 30, 45, 60, 75, 120],
        labels=["<18", "18-30", "31-45", "46-60", "61-75", "76+"],
    )
    return df


# ------------------------------------------------------------- sidebar
st.sidebar.title("🏥 Filters")
dedupe = st.sidebar.checkbox("Remove duplicate rows", value=True)
df = load_data(dedupe)

min_d, max_d = df["Date of Admission"].min().date(), df["Date of Admission"].max().date()
date_range = st.sidebar.date_input("Admission date", (min_d, max_d), min_value=min_d, max_value=max_d)

conditions = st.sidebar.multiselect("Medical condition", sorted(df["Medical Condition"].unique()))
adm_types = st.sidebar.multiselect("Admission type", sorted(df["Admission Type"].unique()))
insurers = st.sidebar.multiselect("Insurance provider", sorted(df["Insurance Provider"].unique()))
genders = st.sidebar.multiselect("Gender", sorted(df["Gender"].unique()))
age_min, age_max = int(df["Age"].min()), int(df["Age"].max())
age_range = st.sidebar.slider("Age", age_min, age_max, (age_min, age_max))
hide_neg = st.sidebar.checkbox("Exclude negative billing amounts", value=False)
st.sidebar.caption("Empty multiselect = all values.")

f = df.copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    f = f[f["Date of Admission"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]
for col, sel in [
    ("Medical Condition", conditions),
    ("Admission Type", adm_types),
    ("Insurance Provider", insurers),
    ("Gender", genders),
]:
    if sel:
        f = f[f[col].isin(sel)]
f = f[f["Age"].between(*age_range)]
if hide_neg:
    f = f[f["Billing Amount"] >= 0]

# ---------------------------------------------------------------- header
st.title("Healthcare Admissions Dashboard")
st.caption(f"{len(f):,} of {len(df):,} admissions match the current filters")

if f.empty:
    st.warning("No records match these filters.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Admissions", f"{len(f):,}")
k2.metric("Total billing", f"${f['Billing Amount'].sum() / 1e6:,.1f}M")
k3.metric("Avg billing", f"${f['Billing Amount'].mean():,.0f}")
k4.metric("Avg length of stay", f"{f['Length of Stay'].mean():.1f} days")
k5.metric("Abnormal results", f"{(f['Test Results'] == 'Abnormal').mean():.1%}")

tab_over, tab_fin, tab_pat, tab_clin, tab_data = st.tabs(
    ["📈 Overview", "💰 Billing", "🧑 Patients", "🧪 Clinical", "📋 Data"]
)

# -------------------------------------------------------------- overview
with tab_over:
    monthly = f.groupby("Admission Month").size().reset_index(name="Admissions")
    st.plotly_chart(
        px.line(monthly, x="Admission Month", y="Admissions", title="Monthly admissions", markers=True),
        width="stretch",
    )
    c1, c2 = st.columns(2)
    cond = f["Medical Condition"].value_counts().reset_index()
    c1.plotly_chart(
        px.bar(cond, x="count", y="Medical Condition", orientation="h", title="Admissions by condition"),
        width="stretch",
    )
    c2.plotly_chart(
        px.pie(f, names="Admission Type", hole=0.45, title="Admission type mix"),
        width="stretch",
    )
    trend = (
        f.groupby(["Admission Month", "Admission Type"]).size().reset_index(name="Admissions")
    )
    st.plotly_chart(
        px.area(trend, x="Admission Month", y="Admissions", color="Admission Type",
                title="Admission type over time"),
        width="stretch",
    )

# --------------------------------------------------------------- billing
with tab_fin:
    c1, c2 = st.columns(2)
    c1.plotly_chart(
        px.histogram(f, x="Billing Amount", nbins=50, title="Billing amount distribution"),
        width="stretch",
    )
    by_ins = f.groupby("Insurance Provider")["Billing Amount"].agg(["mean", "sum"]).reset_index()
    c2.plotly_chart(
        px.bar(by_ins, x="Insurance Provider", y="mean", title="Average billing by insurer",
               labels={"mean": "Avg billing ($)"}),
        width="stretch",
    )
    c3, c4 = st.columns(2)
    c3.plotly_chart(
        px.box(f, x="Medical Condition", y="Billing Amount", title="Billing by condition"),
        width="stretch",
    )
    yearly = f.groupby(f["Date of Admission"].dt.year)["Billing Amount"].sum().reset_index()
    yearly.columns = ["Year", "Total billing"]
    c4.plotly_chart(
        px.bar(yearly, x="Year", y="Total billing", title="Total billing per year (2024 is partial)"),
        width="stretch",
    )
    neg = (f["Billing Amount"] < 0).sum()
    if neg:
        st.info(f"{neg} records have a negative billing amount (refunds or data errors). "
                "Use the sidebar toggle to exclude them.")

# -------------------------------------------------------------- patients
with tab_pat:
    c1, c2 = st.columns(2)
    c1.plotly_chart(
        px.histogram(f, x="Age", nbins=30, color="Gender", barmode="overlay", opacity=0.7,
                     title="Age distribution by gender"),
        width="stretch",
    )
    bt = f["Blood Type"].value_counts().reset_index()
    c2.plotly_chart(px.bar(bt, x="Blood Type", y="count", title="Blood type"), width="stretch")
    heat = pd.crosstab(f["Age Group"], f["Medical Condition"])
    st.plotly_chart(
        px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale="Blues",
                  title="Age group × condition"),
        width="stretch",
    )

# -------------------------------------------------------------- clinical
with tab_clin:
    c1, c2 = st.columns(2)
    tr = pd.crosstab(f["Medical Condition"], f["Test Results"], normalize="index").reset_index().melt(
        id_vars="Medical Condition", value_name="Share"
    )
    c1.plotly_chart(
        px.bar(tr, x="Medical Condition", y="Share", color="Test Results", barmode="stack",
               title="Test results by condition"),
        width="stretch",
    )
    c2.plotly_chart(
        px.histogram(f, x="Length of Stay", nbins=30, title="Length of stay (days)"),
        width="stretch",
    )
    med = pd.crosstab(f["Medical Condition"], f["Medication"])
    st.plotly_chart(
        px.imshow(med, text_auto=True, aspect="auto", color_continuous_scale="Teal",
                  title="Medication × condition"),
        width="stretch",
    )
    los = f.groupby("Admission Type")["Length of Stay"].mean().reset_index()
    st.plotly_chart(
        px.bar(los, x="Admission Type", y="Length of Stay", title="Avg length of stay by admission type"),
        width="stretch",
    )

# ------------------------------------------------------------------ data
with tab_data:
    st.dataframe(f.drop(columns=["Admission Month"]), width="stretch", height=450)
    st.download_button(
        "Download filtered data (CSV)",
        f.drop(columns=["Admission Month"]).to_csv(index=False).encode(),
        file_name="filtered_healthcare_data.csv",
        mime="text/csv",
    )
    st.subheader("Summary statistics")
    st.dataframe(f[["Age", "Billing Amount", "Length of Stay"]].describe().T, width="stretch")
