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
.main-title {font-size:28px;font-weight:700;color:#111;}
.sub-title {color:#666;font-size:14px;margin-bottom:1.2rem;}
.kpi-card {border:1px solid #d9d9d9;border-radius:14px;padding:14px;background:white;text-align:center;}
.kpi-title {font-size:13px;color:#555;}
.kpi-value {font-size:26px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# LOGIN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == st.secrets["dashboard_username"] and password == st.secrets["dashboard_password"]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect credentials")
    st.stop()

# ----------------------------
# GOOGLE CONNECTION
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

# 🔥 NEW: TITHES
try:
    tithes = pd.DataFrame(client.open("ChurchApp").worksheet("Tithes").get_all_records())
except:
    tithes = pd.DataFrame(columns=["Cellphone", "Name", "Surname", "Amount", "Date"])

# Clean columns
for df in [members, attendance, tithes]:
    if not df.empty:
        df.columns = df.columns.str.strip()

# Ensure columns exist
for col in ["Cellphone", "Name", "Surname", "Amount", "Date"]:
    if col not in tithes.columns:
        tithes[col] = ""

# Convert types
tithes["Amount"] = pd.to_numeric(tithes["Amount"], errors="coerce").fillna(0)
tithes["Date"] = pd.to_datetime(tithes["Date"], errors="coerce")

# ----------------------------
# TABS (SAFE)
# ----------------------------
tab1, tab2 = st.tabs(["📊 Dashboard", "💰 Tithing"])

# ----------------------------
# DASHBOARD (UNCHANGED AREA)
# ----------------------------
with tab1:

    st.markdown("<div class='main-title'>📊 Church Executive Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Overview</div>", unsafe_allow_html=True)

    # SIMPLE KPIs (keeps your app alive)
    total_members = len(members)
    total_attendance = len(attendance)

    col1, col2 = st.columns(2)
    col1.metric("Members", total_members)
    col2.metric("Attendance Records", total_attendance)

    # Attendance Trend
    if not attendance.empty:
        attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")
        daily = attendance.groupby("Date").size().reset_index(name="count")
        fig = px.line(daily, x="Date", y="count", title="Attendance Trend")
        st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# 💰 TITHING TAB (NEW FEATURE)
# ----------------------------
with tab2:

    st.markdown("<div class='main-title'>💰 Tithing Overview</div>", unsafe_allow_html=True)

    if tithes.empty:
        st.warning("No tithing data available.")
    else:

        # FILTER
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", tithes["Date"].min())
        end_date = col2.date_input("End Date", tithes["Date"].max())

        filtered = tithes[
            (tithes["Date"] >= pd.to_datetime(start_date)) &
            (tithes["Date"] <= pd.to_datetime(end_date))
        ]

        # AGGREGATION
        member_totals = (
            filtered
            .groupby(["Cellphone", "Name", "Surname"], as_index=False)
            .agg(Total_Amount=("Amount", "sum"))
        )

        # KPIs
        total = filtered["Amount"].sum()
        members_count = len(member_totals)
        avg = member_totals["Total_Amount"].mean() if members_count > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Tithes", f"R{total:,.0f}")
        k2.metric("Tithing Members", members_count)
        k3.metric("Avg per Member", f"R{avg:,.0f}")

        # TABLE
        st.subheader("📋 Tithing Members")
        st.dataframe(member_totals, use_container_width=True)

        # TREND
        st.subheader("📈 Tithing Trend")
        daily = filtered.groupby("Date")["Amount"].sum().reset_index()
        fig = px.line(daily, x="Date", y="Amount")
        st.plotly_chart(fig, use_container_width=True)
