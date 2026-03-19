import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Intelligence System", layout="wide")

# ----------------------------
# GOOGLE SHEETS CONNECTION
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
# LOGIN SYSTEM
# ----------------------------
def load_users():
    return pd.DataFrame(client.open("ChurchApp").worksheet("Users").get_all_records())

def login():
    users = load_users()

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users.columns = users.columns.str.strip().str.lower()
        users["email"] = users["email"].str.strip().str.lower()
        users["password"] = users["password"].astype(str).str.strip()

        user = users[
            (users["email"] == email.strip().lower()) &
            (users["password"] == password.strip())
        ]

        if not user.empty:
            st.session_state["logged_in"] = True
            st.session_state["church"] = user.iloc[0]["church"]
            st.rerun()
        else:
            st.error("Invalid credentials")

# ----------------------------
# SESSION CONTROL
# ----------------------------
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

members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# AUTO FIRST VISIT
# ----------------------------
today = datetime.now().strftime("%Y-%m-%d")

for _, m in members.iterrows():
    if attendance[attendance["MemberID"] == str(m["MemberID"])].empty:
        client.open("ChurchApp").worksheet("Attendance").append_row([
            today,
            datetime.now().strftime("%H:%M"),
            "Auto Registration",
            m["MemberID"],
            m["First Name"] + " " + m["Surname"],
            "First Visit",
            m["Province"],
            m["Branch"],
            m["Gender"],
            m["Region"],
            m["Employment Status"]
        ])

# ----------------------------
# FILTER
# ----------------------------
church = st.session_state.get("church")
members = members[members["Branch"] == church]
attendance = attendance[attendance["Branch"] == church]

st.sidebar.header("Filters")

gender = st.sidebar.multiselect("Gender", members["Gender"].unique(), default=members["Gender"].unique())
province = st.sidebar.multiselect("Province", members["Province"].unique(), default=members["Province"].unique())
branch = st.sidebar.multiselect("Branch", members["Branch"].unique(), default=members["Branch"].unique())
region = st.sidebar.multiselect("Region", members["Region"].unique(), default=members["Region"].unique())
employment = st.sidebar.multiselect("Employment Status", members["Employment Status"].unique(), default=members["Employment Status"].unique())

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
# KPIs
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
# EMPLOYMENT CHART
# ----------------------------
st.subheader("Employment Status")
emp_df = members_f["Employment Status"].value_counts().reset_index()
emp_df.columns = ["Employment Status", "Count"]
st.plotly_chart(px.bar(emp_df, x="Employment Status", y="Count"))

# ----------------------------
# ATTENDANCE BY SERVICE
# ----------------------------
st.subheader("Attendance by Service")
service_df = attendance_f["Service"].value_counts().reset_index()
service_df.columns = ["Service", "Count"]
st.plotly_chart(px.bar(service_df, x="Service", y="Count"))

# ----------------------------
# GROWTH
# ----------------------------
st.subheader("Growth Over Time")

mem_growth = members_f.groupby(members_f["Timestamp"].dt.date).size().reset_index(name="Members")
att_growth = attendance_f.groupby(attendance_f["Date"].dt.date).size().reset_index(name="Attendance")

growth = pd.merge(mem_growth, att_growth, on="Timestamp", how="outer").fillna(0)

st.plotly_chart(px.line(growth, x="Timestamp", y=["Members", "Attendance"], markers=True))

# ----------------------------
# TOP MEMBERS (FIXED)
# ----------------------------
st.subheader("Top Members")

top = attendance_f["Name"].value_counts().head(10).reset_index()
top.columns = ["Name", "Count"]

st.plotly_chart(px.bar(top, x="Count", y="Name", orientation="h"))

# ----------------------------
# TIME ANALYSIS
# ----------------------------
attendance_f["Hour"] = attendance_f["Time"].str[:2]
time_df = attendance_f["Hour"].value_counts().sort_index().reset_index()
time_df.columns = ["Hour", "Count"]

st.plotly_chart(px.bar(time_df, x="Hour", y="Count"))

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
