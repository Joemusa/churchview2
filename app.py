import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

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
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users.columns = users.columns.str.strip().str.lower()
        users["email"] = users["email"].str.lower().str.strip()
        users["password"] = users["password"].astype(str).str.strip()

        user = users[
            (users["email"] == email.lower().strip()) &
            (users["password"] == password.strip())
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
    "Cellphone?": "Cellphone",
    "Employment Status?": "Employment Status"
})

# Convert dates safely
members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# FILTER CHURCH
# ----------------------------
church = st.session_state.get("church")
members = members[members["Branch"] == church]
attendance = attendance[attendance["Branch"] == church]

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("Filters")

gender = st.sidebar.multiselect("Gender", members["Gender"].dropna().unique(), default=members["Gender"].dropna().unique())
province = st.sidebar.multiselect("Province", members["Province"].dropna().unique(), default=members["Province"].dropna().unique())
branch = st.sidebar.multiselect("Branch", members["Branch"].dropna().unique(), default=members["Branch"].dropna().unique())
region = st.sidebar.multiselect("Region", members["Region"].dropna().unique(), default=members["Region"].dropna().unique())
employment = st.sidebar.multiselect("Employment Status", members["Employment Status"].dropna().unique(), default=members["Employment Status"].dropna().unique())

members_f = members[
    (members["Gender"].isin(gender)) &
    (members["Province"].isin(province)) &
    (members["Branch"].isin(branch)) &
    (members["Region"].isin(region)) &
    (members["Employment Status"].isin(employment))
]

attendance_f = attendance[
    (attendance["Gender"].isin(gender)) &
    (attendance["Province"].isin(province)) &
    (attendance["Branch"].isin(branch)) &
    (attendance["Region"].isin(region)) &
    (attendance["Employment Status"].isin(employment))
]

# ----------------------------
# KPI
# ----------------------------
st.title("⛪ Church Dashboard")

c1, c2, c3 = st.columns(3)
c1.metric("Members", len(members_f))
c2.metric("Attendance", len(attendance_f))
c3.metric("First Visits", len(attendance_f[attendance_f["Status"] == "First Visit"]))

# ----------------------------
# MEMBERS CHART
# ----------------------------
st.subheader("Members by Gender")
st.plotly_chart(px.pie(members_f, names="Gender"))

# ----------------------------
# EMPLOYMENT
# ----------------------------
emp = members_f["Employment Status"].value_counts().reset_index()
emp.columns = ["Employment Status", "Count"]
st.plotly_chart(px.bar(emp, x="Employment Status", y="Count"))

# ----------------------------
# ATTENDANCE SERVICE
# ----------------------------
service = attendance_f["Service"].value_counts().reset_index()
service.columns = ["Service", "Count"]
st.plotly_chart(px.bar(service, x="Service", y="Count"))

# ----------------------------
# GROWTH FIXED
# ----------------------------
st.subheader("Growth Over Time")

mem_growth = members_f.groupby(members_f["Timestamp"].dt.date).size().reset_index(name="Members")
mem_growth.columns = ["Date", "Members"]

att_growth = attendance_f.groupby(attendance_f["Date"].dt.date).size().reset_index(name="Attendance")
att_growth.columns = ["Date", "Attendance"]

growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

st.plotly_chart(px.line(growth, x="Date", y=["Members", "Attendance"], markers=True))

# ----------------------------
# TOP MEMBERS FIXED
# ----------------------------
top = attendance_f["Name"].value_counts().head(10).reset_index()
top.columns = ["Name", "Count"]

st.plotly_chart(px.bar(top, x="Count", y="Name", orientation="h"))

# ----------------------------
# TIME ANALYSIS
# ----------------------------
attendance_f["Hour"] = attendance_f["Time"].astype(str).str[:2]
time_df = attendance_f["Hour"].value_counts().sort_index().reset_index()
time_df.columns = ["Hour", "Count"]

st.plotly_chart(px.bar(time_df, x="Hour", y="Count"))

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
