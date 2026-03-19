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
    sheet = client.open("ChurchApp").worksheet("Users")
    return pd.DataFrame(sheet.get_all_records())

def login():
    df_users = load_users()

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        df_users.columns = [str(col).strip().lower() for col in df_users.columns]
        df_users["email"] = df_users["email"].astype(str).str.strip().str.lower()
        df_users["password"] = df_users["password"].astype(str).str.strip()

        user = df_users[
            (df_users["email"] == email.strip().lower()) &
            (df_users["password"] == password.strip())
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
members_sheet = client.open("ChurchApp").worksheet("Members")
attendance_sheet = client.open("ChurchApp").worksheet("Attendance")

df = pd.DataFrame(members_sheet.get_all_records())
attendance_df = pd.DataFrame(attendance_sheet.get_all_records())

# ----------------------------
# CLEAN DATA
# ----------------------------
df.columns = df.columns.str.strip()
attendance_df.columns = attendance_df.columns.str.strip()

df = df.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Cellphone?": "Cellphone",
    "Employment Status?": "Employment Status"
})

df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
attendance_df["Date"] = pd.to_datetime(attendance_df["Date"], errors="coerce")

# ----------------------------
# AUTO FIRST VISIT
# ----------------------------
today = datetime.now().strftime("%Y-%m-%d")

for _, member in df.iterrows():
    member_id = str(member["MemberID"])

    existing = attendance_df[
        attendance_df["MemberID"] == member_id
    ]

    if existing.empty:
        attendance_sheet.append_row([
            today,
            datetime.now().strftime("%H:%M"),
            "Auto Registration",
            member_id,
            member["First Name"] + " " + member["Surname"],
            "First Visit",
            member["Province"],
            member["Branch"],
            member["Gender"],
            member["Region"],
            member["Employment Status"]
        ])

# ----------------------------
# FILTER BY CHURCH
# ----------------------------
church = st.session_state.get("church")
df = df[df["Branch"] == church]
attendance_df = attendance_df[attendance_df["Branch"] == church]

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender_filter = st.sidebar.multiselect(
    "Gender",
    sorted(df["Gender"].dropna().unique()),
    default=sorted(df["Gender"].dropna().unique())
)

province_filter = st.sidebar.multiselect(
    "Province",
    sorted(df["Province"].dropna().unique()),
    default=sorted(df["Province"].dropna().unique())
)

branch_filter = st.sidebar.multiselect(
    "Branch",
    sorted(df["Branch"].dropna().unique()),
    default=sorted(df["Branch"].dropna().unique())
)

region_filter = st.sidebar.multiselect(
    "Region",
    sorted(df["Region"].dropna().unique()),
    default=sorted(df["Region"].dropna().unique())
)

employment_filter = st.sidebar.multiselect(
    "Employment Status",
    sorted(df["Employment Status"].dropna().unique()),
    default=sorted(df["Employment Status"].dropna().unique())
)

# Apply filters
filtered_df = df[
    (df["Gender"].isin(gender_filter)) &
    (df["Province"].isin(province_filter)) &
    (df["Branch"].isin(branch_filter)) &
    (df["Region"].isin(region_filter)) &
    (df["Employment Status"].isin(employment_filter))
]

filtered_attendance = attendance_df[
    (attendance_df["Gender"].isin(gender_filter)) &
    (attendance_df["Province"].isin(province_filter)) &
    (attendance_df["Branch"].isin(branch_filter)) &
    (attendance_df["Region"].isin(region_filter)) &
    (attendance_df["Employment Status"].isin(employment_filter))
]

# ----------------------------
# KPIs
# ----------------------------
st.title("⛪ Church Intelligence Dashboard")

col1, col2, col3 = st.columns(3)

col1.metric("👥 Total Members", len(filtered_df))
col2.metric("📊 Total Attendance", len(filtered_attendance))
col3.metric("🆕 First Visits", len(filtered_attendance[filtered_attendance["Status"] == "First Visit"]))

# ----------------------------
# MEMBERS ANALYSIS
# ----------------------------
st.header("👥 Members Analysis")

col1, col2 = st.columns(2)

with col1:
    fig = px.pie(filtered_df, names="Gender", title="Members by Gender")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(filtered_df["Province"].value_counts(), title="Members by Province")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# EMPLOYMENT ANALYSIS
# ----------------------------
st.subheader("💼 Employment Status")

fig = px.bar(
    filtered_df["Employment Status"].value_counts(),
    title="Employment Distribution"
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# ATTENDANCE ANALYSIS
# ----------------------------
st.header("📊 Attendance Analysis")

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(filtered_attendance["Service"].value_counts(), title="Attendance by Service")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.pie(filtered_attendance, names="Status", title="Attendance Status")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# GROWTH CHART
# ----------------------------
st.header("📈 Growth: Members vs Attendance")

members_growth = filtered_df.groupby(filtered_df["Timestamp"].dt.date).size()
attendance_growth = filtered_attendance.groupby(filtered_attendance["Date"].dt.date).size()

growth_df = pd.DataFrame({
    "Members": members_growth,
    "Attendance": attendance_growth
}).fillna(0)

fig = px.line(growth_df, title="Growth Over Time", markers=True)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# TOP MEMBERS
# ----------------------------
st.header("🏆 Top Members")

top_members = filtered_attendance["Name"].value_counts().head(10)

fig = px.bar(
    x=top_members.values,
    y=top_members.index,
    orientation="h",
    title="Top Attending Members"
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# TIME ANALYSIS
# ----------------------------
filtered_attendance["Hour"] = filtered_attendance["Time"].str[:2]

fig = px.bar(
    filtered_attendance["Hour"].value_counts().sort_index(),
    title="Check-in Times"
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
