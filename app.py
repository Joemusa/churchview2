import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Church Dashboard", layout="wide")

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
# LOAD DATA (FULL DATASET)
# ----------------------------
members = pd.DataFrame(client.open("ChurchApp").worksheet("Members").get_all_records())
attendance = pd.DataFrame(client.open("ChurchApp").worksheet("Attendance").get_all_records())

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
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender = st.sidebar.multiselect("Gender", members["Gender"].dropna().unique(), default=members["Gender"].dropna().unique())
province = st.sidebar.multiselect("Province", members["Province"].dropna().unique(), default=members["Province"].dropna().unique())
region = st.sidebar.multiselect("Region", members["Region"].dropna().unique(), default=members["Region"].dropna().unique())
employment = st.sidebar.multiselect("Employment", members["Employment Status"].dropna().unique(), default=members["Employment Status"].dropna().unique())

# ----------------------------
# FILTERED DATA (ONLY FOR CHARTS)
# ----------------------------
members_f = members[
    (members["Gender"].isin(gender)) &
    (members["Province"].isin(province)) &
    (members["Region"].isin(region)) &
    (members["Employment Status"].isin(employment))
]

attendance_f = attendance.copy()

# ----------------------------
# TITLE
# ----------------------------
st.title("⛪ Church Dashboard")

# ----------------------------
# KPI (USE FULL DATA)
# ----------------------------
k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Members", members["MemberID"].nunique())  # ✅ FIXED
k2.metric("Filtered Members", len(members_f))
k3.metric("Attendance", len(attendance_f))
k4.metric("Branches", members["Branch"].nunique())

# ----------------------------
# TABS
# ----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "📈 Growth",
    "👥 Members",
    "📋 Attendance"
])

# ============================
# DASHBOARD (USES FILTERED DATA)
# ============================
with tab1:

    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(px.pie(members_f, names="Gender", title="Gender"), use_container_width=True)

    with c2:
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment Status", "Count"]
        st.plotly_chart(px.bar(emp, x="Employment Status", y="Count"), use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]
        st.plotly_chart(px.bar(prov, x="Province", y="Count"), use_container_width=True)

    with c4:
        if "Service" in attendance_f.columns:
            serv = attendance_f["Service"].value_counts().reset_index()
            serv.columns = ["Service", "Count"]
            st.plotly_chart(px.bar(serv, x="Service", y="Count"), use_container_width=True)

# ============================
# GROWTH
# ============================
with tab2:

    mem_growth = members.groupby(members["Timestamp"].dt.date).size().reset_index(name="Members")
    mem_growth.columns = ["Date", "Members"]

    att_growth = attendance.groupby(attendance["Date"].dt.date).size().reset_index(name="Attendance")
    att_growth.columns = ["Date", "Attendance"]

    growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

    st.plotly_chart(px.line(growth, x="Date", y=["Members", "Attendance"]), use_container_width=True)

# ============================
# MEMBERS TABLE (FULL DATA)
# ============================
with tab3:
    st.subheader("All Members (Google Sheet)")
    st.dataframe(members, use_container_width=True)  # ✅ FIXED

# ============================
# ATTENDANCE TABLE
# ============================
with tab4:
    st.dataframe(attendance, use_container_width=True)

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
