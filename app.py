import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Church Executive Dashboard", layout="wide")

# ----------------------------
# CUSTOM STYLING
# ----------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: #111111;
    }
    .sub-title {
        color: #666666;
        font-size: 14px;
        margin-bottom: 1.2rem;
    }
    .kpi-card {
        border: 1px solid #d9d9d9;
        border-radius: 14px;
        padding: 14px 12px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        color: #1f1f1f;
    }
    .kpi-title {
        font-size: 13px;
        color: #555555;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        margin-top: 6px;
        color: #111111;
    }
    .chart-card {
        border: 1px solid #d9d9d9;
        border-radius: 16px;
        padding: 12px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 14px;
    }
    .login-card {
        max-width: 420px;
        margin: 60px auto;
        border: 1px solid #d9d9d9;
        border-radius: 18px;
        padding: 28px;
        background: white;
        box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# SIMPLE LOGIN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

APP_USERNAME = st.secrets.get("dashboard_username", "admin")
APP_PASSWORD = st.secrets.get("dashboard_password", "admin123")

if not st.session_state.logged_in:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("<div class='main-title'>🔐 Login</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Church Executive Dashboard</div>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect username or password")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------------------
# CONNECT
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

# ----------------------------
# LOAD DATA
# ----------------------------
members = pd.DataFrame(client.open("ChurchApp").worksheet("Members").get_all_records())
attendance = pd.DataFrame(client.open("ChurchApp").worksheet("Attendance").get_all_records())

if not members.empty:
    members.columns = members.columns.str.strip()

if not attendance.empty:
    attendance.columns = attendance.columns.str.strip()

members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Employment Status?": "Employment Status",
    "Cellphone?": "Cellphone"
})
st.write("Members shape:", members.shape)
st.write("Attendance shape:", attendance.shape)
st.dataframe(members.head())
st.dataframe(attendance.head())
# ----------------------------
# ENSURE EXPECTED COLUMNS
# ----------------------------
for col in ["Gender", "Province", "Region", "Employment Status", "Branch", "Age", "MemberID", "First Name", "Surname", "Cellphone"]:
    if col not in members.columns:
        members[col] = ""

for col in ["Date", "Service", "MemberID", "Name", "Status", "Contact"]:
    if col not in attendance.columns:
        attendance[col] = ""

if "Timestamp" not in members.columns:
    members["Timestamp"] = pd.NaT

# ----------------------------
# STANDARDIZE KEYS
# ----------------------------
members["MemberID"] = members["MemberID"].astype(str).str.strip()
attendance["MemberID"] = attendance["MemberID"].astype(str).str.strip()

members["Full Name"] = (
    members["First Name"].astype(str).str.strip() + " " +
    members["Surname"].astype(str).str.strip()
).str.strip()

# Convert dates
members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender_options = sorted([x for x in members["Gender"].dropna().unique() if str(x).strip() != ""])
province_options = sorted([x for x in members["Province"].dropna().unique() if str(x).strip() != ""])
region_options = sorted([x for x in members["Region"].dropna().unique() if str(x).strip() != ""])
employment_options = sorted([x for x in members["Employment Status"].dropna().unique() if str(x).strip() != ""])

gender = st.sidebar.multiselect("Gender", gender_options, default=gender_options)
province = st.sidebar.multiselect("Province", province_options, default=province_options)
region = st.sidebar.multiselect("Region", region_options, default=region_options)
employment = st.sidebar.multiselect("Employment Status", employment_options, default=employment_options)

# ----------------------------
# APPLY FILTERS
# ----------------------------
filtered_members = members[
    (members["Gender"].isin(gender)) &
    (members["Province"].isin(province)) &
    (members["Region"].isin(region)) &
    (members["Employment Status"].isin(employment))
]

# ----------------------------
# DASHBOARD TITLE
# ----------------------------
st.markdown("<div class='main-title'>📊 Church Executive Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Live overview of members and attendance</div>", unsafe_allow_html=True)

# ----------------------------
# KPIs
# ----------------------------
total_members = len(filtered_members)
total_attendance = len(attendance)

col1, col2 = st.columns(2)

col1.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Total Members</div>
    <div class="kpi-value">{total_members}</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
    <div class="kpi-title">Total Attendance Records</div>
    <div class="kpi-value">{total_attendance}</div>
</div>
""", unsafe_allow_html=True)

# ----------------------------
# ATTENDANCE TREND
# ----------------------------
if not attendance.empty:
    attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

    daily_attendance = attendance.groupby("Date").size().reset_index(name="Attendance")

    fig = px.line(
        daily_attendance,
        x="Date",
        y="Attendance",
        title="Attendance Trend Over Time"
    )

    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# MEMBERS TABLE
# ----------------------------
st.markdown("### 👥 Members Overview")
st.dataframe(filtered_members, use_container_width=True)
