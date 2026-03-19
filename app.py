import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Church Dashboard",
    layout="wide"
)

# ----------------------------
# RESPONSIVE DETECTION
# ----------------------------
screen_width = st.sidebar.slider("Screen Width (simulate)", 300, 1600, 1200)

def get_columns():
    if screen_width < 600:
        return 1   # mobile
    elif screen_width < 1000:
        return 2   # tablet
    else:
        return 2   # desktop (we keep 2 for clean look)

cols = get_columns()

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
# TITLE
# ----------------------------
st.title("⛪ Church Dashboard")

# ----------------------------
# KPI (Responsive)
# ----------------------------
kpis = [
    ("Members", len(members_f)),
    ("Attendance", len(attendance_f)),
    ("First Visits", len(attendance_f[attendance_f["Status"] == "First Visit"])),
    ("Branches", members_f["Branch"].nunique())
]

for i in range(0, len(kpis), cols):
    row = st.columns(cols)
    for j in range(cols):
        if i + j < len(kpis):
            label, value = kpis[i + j]
            row[j].metric(label, value)

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

    charts = [
        px.pie(members_f, names="Gender", title="Gender"),
        px.bar(members_f["Employment Status"].value_counts().reset_index(),
               x="index", y="Employment Status", title="Employment"),
        px.bar(members_f["Province"].value_counts().reset_index(),
               x="index", y="Province", title="Province"),
        px.bar(attendance_f["Service"].value_counts().reset_index(),
               x="index", y="Service", title="Service")
    ]

    for i in range(0, len(charts), cols):
        row = st.columns(cols)
        for j in range(cols):
            if i + j < len(charts):
                row[j].plotly_chart(charts[i + j], use_container_width=True)

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
