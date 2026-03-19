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
# LOAD DATA
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
# FILTER
# ----------------------------
church = st.session_state.get("church")
members = members[members["Branch"] == church]
attendance = attendance[attendance["Branch"] == church]

st.sidebar.header("Filters")

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
    (attendance["Employment Status"].isin(employment)) &
    (attendance["Service"].isin(service))
]

# ----------------------------
# TITLE
# ----------------------------
st.title("⛪ Church Dashboard")

# ----------------------------
# KPI
# ----------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Members", len(members_f))
k2.metric("Attendance", len(attendance_f))
k3.metric("First Visits", len(attendance_f[attendance_f["Status"] == "First Visit"]))
k4.metric("Branches", members_f["Branch"].nunique())

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
# DASHBOARD
# ============================
with tab1:

    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(px.pie(members_f, names="Gender", title="Gender"), use_container_width=True)

    with c2:
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment Status", "Count"]
        st.plotly_chart(px.bar(emp, x="Employment Status", y="Count", title="Employment"), use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]
        st.plotly_chart(px.bar(prov, x="Province", y="Count", title="Province"), use_container_width=True)

    with c4:
        serv = attendance_f["Service"].value_counts().reset_index()
        serv.columns = ["Service", "Count"]
        st.plotly_chart(px.bar(serv, x="Service", y="Count", title="Service"), use_container_width=True)

# ============================
# GROWTH
# ============================
with tab2:

    mem_growth = members_f.groupby(members_f["Timestamp"].dt.date).size().reset_index(name="Members")
    mem_growth.columns = ["Date", "Members"]

    att_growth = attendance_f.groupby(attendance_f["Date"].dt.date).size().reset_index(name="Attendance")
    att_growth.columns = ["Date", "Attendance"]

    growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

    st.plotly_chart(px.line(growth, x="Date", y=["Members", "Attendance"]), use_container_width=True)

# ============================
# MEMBERS
# ============================
with tab3:
    st.dataframe(members_f, use_container_width=True)

# ============================
# ATTENDANCE
# ============================
with tab4:
    st.dataframe(attendance_f, use_container_width=True)

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
