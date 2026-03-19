import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Intelligence Dashboard", layout="wide")

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
# LOGIN
# ----------------------------
def load_users():
    return pd.DataFrame(client.open("ChurchApp").worksheet("Users").get_all_records())

def login():
    users = load_users()

    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users.columns = users.columns.str.strip().str.lower()

        user = users[
            (users["email"].str.lower().str.strip() == email.lower().strip()) &
            (users["password"].astype(str).str.strip() == password.strip())
        ]

        if not user.empty:
            st.session_state["logged_in"] = True
            st.session_state["church"] = user.iloc[0]["church"]
            st.rerun()
        else:
            st.error("Invalid credentials")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ----------------------------
# LOAD DATA
# ----------------------------
members_sheet = client.open("ChurchApp").worksheet("Members")
attendance_sheet = client.open("ChurchApp").worksheet("Attendance")

members = pd.DataFrame(members_sheet.get_all_records())
attendance = pd.DataFrame(attendance_sheet.get_all_records())

members.columns = members.columns.str.strip()
attendance.columns = attendance.columns.str.strip()

members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Employment Status?": "Employment Status"
})

members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# FILTER BY CHURCH
# ----------------------------
church = st.session_state.get("church")
members = members[members["Branch"] == church]
attendance = attendance[attendance["Branch"] == church]

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender = st.sidebar.multiselect("Gender", members["Gender"].unique(), default=members["Gender"].unique())
province = st.sidebar.multiselect("Province", members["Province"].unique(), default=members["Province"].unique())
region = st.sidebar.multiselect("Region", members["Region"].unique(), default=members["Region"].unique())
employment = st.sidebar.multiselect("Employment", members["Employment Status"].unique(), default=members["Employment Status"].unique())

members_f = members[
    (members["Gender"].isin(gender)) &
    (members["Province"].isin(province)) &
    (members["Region"].isin(region)) &
    (members["Employment Status"].isin(employment))
]

attendance_f = attendance[
    (attendance["Gender"].isin(gender)) &
    (attendance["Province"].isin(province)) &
    (attendance["Region"].isin(region)) &
    (attendance["Employment Status"].isin(employment))
]

# ----------------------------
# HEADER
# ----------------------------
st.title("⛪ Church Intelligence Dashboard")

# ----------------------------
# KPI
# ----------------------------
k1, k2, k3, k4 = st.columns(4)

k1.metric("Members", len(members_f))
k2.metric("Attendance", len(attendance_f))
k3.metric("First Visits", len(attendance_f[attendance_f["Status"] == "First Visit"]))
k4.metric("Branches", members_f["Branch"].nunique())

# ----------------------------
# MAIN TABS
# ----------------------------
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👥 Members Table", "📋 Attendance Table"])

# ============================
# TAB 1: DASHBOARD
# ============================
with tab1:

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(px.pie(members_f, names="Gender", title="Gender Distribution"), use_container_width=True)

    with col2:
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment", "Count"]
        st.plotly_chart(px.bar(emp, x="Employment", y="Count", title="Employment Status"), use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]
        st.plotly_chart(px.bar(prov, x="Province", y="Count", title="Members by Province"), use_container_width=True)

    with col4:
        serv = attendance_f["Service"].value_counts().reset_index()
        serv.columns = ["Service", "Count"]
        st.plotly_chart(px.bar(serv, x="Service", y="Count", title="Attendance by Service"), use_container_width=True)

# ============================
# TAB 2: MEMBERS TABLE
# ============================
with tab2:

    st.subheader("👥 Members")

    st.dataframe(members_f, use_container_width=True)

    if st.button("📤 Export Members to Google Sheets"):
        export_sheet = client.open("ChurchApp").worksheet("Members_Export")
        export_sheet.clear()
        export_sheet.append_row(list(members_f.columns))
        export_sheet.append_rows(members_f.values.tolist())
        st.success("Members exported successfully!")

# ============================
# TAB 3: ATTENDANCE TABLE
# ============================
with tab3:

    st.subheader("📋 Attendance")

    st.dataframe(attendance_f, use_container_width=True)

    if st.button("📤 Export Attendance to Google Sheets"):
        export_sheet = client.open("ChurchApp").worksheet("Attendance_Export")
        export_sheet.clear()
        export_sheet.append_row(list(attendance_f.columns))
        export_sheet.append_rows(attendance_f.values.tolist())
        st.success("Attendance exported successfully!")

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
