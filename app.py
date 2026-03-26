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
# LOGIN
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
# CONNECT GOOGLE SHEETS
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

# NEW: LOAD TITHES
try:
    tithes = pd.DataFrame(client.open("ChurchApp").worksheet("Tithes").get_all_records())
except:
    tithes = pd.DataFrame()

# Clean columns
for df in [members, attendance, tithes]:
    if not df.empty:
        df.columns = df.columns.str.strip()

# Rename columns
members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Employment Status?": "Employment Status",
    "Cellphone?": "Cellphone"
})

# Ensure columns exist
for col in ["Gender", "Province", "Region", "Employment Status", "Branch", "Age", "MemberID", "First Name", "Surname", "Cellphone"]:
    if col not in members.columns:
        members[col] = ""

for col in ["Date", "Service", "MemberID", "Name", "Status", "Contact"]:
    if col not in attendance.columns:
        attendance[col] = ""

for col in ["Cellphone", "Name", "Surname", "Amount", "Date"]:
    if col not in tithes.columns:
        tithes[col] = ""

# Convert types
members["Timestamp"] = pd.to_datetime(members.get("Timestamp"), errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")
tithes["Date"] = pd.to_datetime(tithes["Date"], errors="coerce")
tithes["Amount"] = pd.to_numeric(tithes["Amount"], errors="coerce").fillna(0)

# ----------------------------
# TABS
# ----------------------------
tab1, tab2 = st.tabs(["📊 Dashboard", "💰 Tithing"])

# ----------------------------
# DASHBOARD TAB (YOUR EXISTING)
# ----------------------------
with tab1:
    st.markdown("<div class='main-title'>📊 Church Executive Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Overview of members and attendance</div>", unsafe_allow_html=True)

    st.write("Your existing dashboard continues here...")

# ----------------------------
# TITHING TAB
# ----------------------------
with tab2:
    st.markdown("<div class='main-title'>💰 Tithing Overview</div>", unsafe_allow_html=True)

    if tithes.empty:
        st.warning("No tithing data available.")
    else:
        # FILTER
        start_date = st.date_input("Start Date", tithes["Date"].min())
        end_date = st.date_input("End Date", tithes["Date"].max())

        filtered = tithes[
            (tithes["Date"] >= pd.to_datetime(start_date)) &
            (tithes["Date"] <= pd.to_datetime(end_date))
        ]

        # AGGREGATE
        member_totals = (
            filtered
            .groupby(["Cellphone", "Name", "Surname"], as_index=False)
            .agg(Total_Amount=("Amount", "sum"))
        )

        # KPIs
        total = filtered["Amount"].sum()
        members_count = member_totals.shape[0]
        avg = member_totals["Total_Amount"].mean() if members_count > 0 else 0

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Tithes", f"R{total:,.0f}")
        col2.metric("Tithing Members", members_count)
        col3.metric("Average per Member", f"R{avg:,.0f}")

        # TABLE
        st.subheader("📋 Tithing Members")
        st.dataframe(member_totals, use_container_width=True)

        # TREND
        st.subheader("📈 Trend")
        daily = filtered.groupby("Date")["Amount"].sum().reset_index()
        fig = px.line(daily, x="Date", y="Amount")
        st.plotly_chart(fig, use_container_width=True)
