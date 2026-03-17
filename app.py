import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Analytics", layout="wide")

# ----------------------------
# CUSTOM STYLE (Power BI Look)
# ----------------------------
st.markdown("""
    <style>
    .metric-card {
        background-color: #1f2937;
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⛪ Church Member Analytics Dashboard")

# ----------------------------
# GOOGLE SHEETS CONNECTION
# ----------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)
sheet = client.open("1l0wrjMGHNcipYqeLkwY15fKPuM7bpwKMvICUuGhNcOs").Members
data = sheet.get_all_records()

df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

# CLEAN DATA
df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

province = st.sidebar.multiselect("Province", df["Province"].unique(), df["Province"].unique())
branch = st.sidebar.multiselect("Branch", df["Branch"].unique(), df["Branch"].unique())

filtered_df = df[
    (df["Province"].isin(province)) &
    (df["Branch"].isin(branch))
]

# ----------------------------
# KPI SECTION (CARDS)
# ----------------------------
col1, col2, col3, col4 = st.columns(4)

total_members = len(filtered_df)
avg_age = filtered_df["Age"].mean()

male = len(filtered_df[filtered_df["Gender"] == "Male"])
female = len(filtered_df[filtered_df["Gender"] == "Female"])

col1.metric("👥 Total Members", total_members)
col2.metric("📊 Avg Age", round(avg_age, 1))
col3.metric("👨 Male", male)
col4.metric("👩 Female", female)

# ----------------------------
# TABS (Power BI Style)
# ----------------------------
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Growth", "📋 Members"])

# ----------------------------
# TAB 1: OVERVIEW
# ----------------------------
with tab1:
    col1, col2 = st.columns(2)

    col1.subheader("Members by Province")
    col1.bar_chart(filtered_df["Province"].value_counts())

    col2.subheader("Members by Branch")
    col2.bar_chart(filtered_df["Branch"].value_counts())

    st.subheader("Employment Status")
    st.bar_chart(filtered_df["Employment Status"].value_counts())

    st.subheader("Age Distribution")
    st.bar_chart(filtered_df["Age"].value_counts().sort_index())

# ----------------------------
# TAB 2: GROWTH TRACKING
# ----------------------------
with tab2:
    st.subheader("📈 Church Growth Over Time")

    growth = filtered_df.copy()
    growth["Date"] = growth["Timestamp"].dt.date

    growth_chart = growth.groupby("Date").size()

    st.line_chart(growth_chart)

    st.markdown("### 🔥 Insight")
    st.write("Track how your church is growing daily. Identify spikes after events or campaigns.")

# ----------------------------
# TAB 3: MEMBER LIST
# ----------------------------
with tab3:
    st.subheader("📋 Member Database")
    st.dataframe(filtered_df)

    st.download_button(
        "⬇ Download Data",
        filtered_df.to_csv(index=False),
        "members.csv"
    )
