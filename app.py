import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Intelligence System", layout="wide")

st.title("⛪ Church Member Dashboard")

# ----------------------------
# GOOGLE SHEETS CONNECTION (SECRETS)
# ----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# 👉 YOUR SHEET NAME
sheet = client.open("Churchview").worksheet("Members")
# Load data
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ----------------------------
# CLEAN DATA
# ----------------------------
df.columns = df.columns.str.strip()

# Rename columns (IMPORTANT if your sheet still has ?)
df = df.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Cellphone?": "Cellphone",
    "Gender?": "Gender",
    "Age?": "Age",
    "Employment Status?": "Employment Status",
    "Province?": "Province",
    "Region?": "Region",
    "Branch?": "Branch"
})

# Convert data types
df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

province = st.sidebar.multiselect(
    "Province",
    options=df["Province"].dropna().unique(),
    default=df["Province"].dropna().unique()
)

branch = st.sidebar.multiselect(
    "Branch",
    options=df["Branch"].dropna().unique(),
    default=df["Branch"].dropna().unique()
)

gender = st.sidebar.multiselect(
    "Gender",
    options=df["Gender"].dropna().unique(),
    default=df["Gender"].dropna().unique()
)

# Apply filters
filtered_df = df[
    (df["Province"].isin(province)) &
    (df["Branch"].isin(branch)) &
    (df["Gender"].isin(gender))
]

# ----------------------------
# KPI SECTION
# ----------------------------
col1, col2, col3, col4 = st.columns(4)

total_members = len(filtered_df)
avg_age = filtered_df["Age"].mean()

male = len(filtered_df[filtered_df["Gender"] == "Male"])
female = len(filtered_df[filtered_df["Gender"] == "Female"])

employment_rate = (
    len(filtered_df[filtered_df["Employment Status"] == "Employed"])
    / total_members * 100 if total_members > 0 else 0
)

col1.metric("👥 Total Members", total_members)
col2.metric("📊 Avg Age", round(avg_age, 1) if pd.notnull(avg_age) else 0)
col3.metric("👨 Male", male)
col4.metric("💼 Employed %", f"{round(employment_rate,1)}%")

# ----------------------------
# TABS
# ----------------------------
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Growth", "📋 Members"])

# ----------------------------
# OVERVIEW
# ----------------------------
with tab1:
    col1, col2 = st.columns(2)

    col1.subheader("Members by Province")
    col1.bar_chart(filtered_df["Province"].value_counts())

    col2.subheader("Members by Branch")
    col2.bar_chart(filtered_df["Branch"].value_counts())

    st.subheader("Gender Distribution")
    st.bar_chart(filtered_df["Gender"].value_counts())

    st.subheader("Employment Status")
    st.bar_chart(filtered_df["Employment Status"].value_counts())

    st.subheader("Age Distribution")
    st.bar_chart(filtered_df["Age"].value_counts().sort_index())

# ----------------------------
# GROWTH TRACKING
# ----------------------------
with tab2:
    st.subheader("📈 Church Growth Over Time")

    growth = filtered_df.copy()
    growth["Date"] = growth["Timestamp"].dt.date

    daily_growth = growth.groupby("Date").size()
    st.line_chart(daily_growth)

    # Monthly Growth
    growth["Month"] = growth["Timestamp"].dt.to_period("M")
    monthly_growth = growth.groupby("Month").size()

    st.subheader("Monthly Growth")
    st.bar_chart(monthly_growth)

# ----------------------------
# MEMBER TABLE
# ----------------------------
with tab3:
    st.subheader("📋 Member List")

    st.dataframe(filtered_df)

    st.download_button(
        "⬇ Download Data",
        filtered_df.to_csv(index=False),
        "church_members.csv"
    )
