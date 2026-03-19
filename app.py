import streamlit as st
import pandas as pd
import gspread
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

client = gspread.authorize(creds)   # ✅ FIXED: client defined FIRST

# ----------------------------
# LOGIN SYSTEM
# ----------------------------
def load_users():
    users_sheet = client.open("ChurchApp").worksheet("Users")
    users_data = users_sheet.get_all_records()
    return pd.DataFrame(users_data)

def login():
    df_users = load_users()

    input_email = st.text_input("Email")
    input_password = st.text_input("Password", type="password")

    if st.button("Login"):

        if not input_email or not input_password:
            st.warning("Please enter email and password")
            return

        email = input_email.strip().lower()
        password = input_password.strip()

        df_users.columns = [str(col).strip().lower() for col in df_users.columns]
        df_users['email'] = df_users['email'].astype(str).str.strip().str.lower()
        df_users['password'] = df_users['password'].astype(str).str.strip()

        user = df_users[
            (df_users['email'] == email) &
            (df_users['password'] == password)
        ]

        if not user.empty:
            st.session_state["logged_in"] = True
            st.session_state["church"] = user.iloc[0]["church"]
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ----------------------------
# SESSION CONTROL
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state.get("logged_in"):
    login()
    st.stop()

# ----------------------------
# MAIN DASHBOARD
# ----------------------------
st.title("⛪ Church Member Dashboard")

# ----------------------------
# LOAD MEMBERS
# ----------------------------
members_sheet = client.open("ChurchApp").worksheet("Members")
members_data = members_sheet.get_all_records()
df = pd.DataFrame(members_data)

df.columns = df.columns.str.strip()

df = df.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Cellphone?": "Cellphone",
    "Gender?": "Gender",
    "Age?": "Age",
    "Employment Status?": "Employment Status",
    "Province?": "Province",
    "Region?": "Region",
    "Branch?": "Branch"
})

df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

# ----------------------------
# LOAD ATTENDANCE
# ----------------------------
attendance_sheet = client.open("ChurchApp").worksheet("Attendance")
attendance_data = attendance_sheet.get_all_records()
attendance_df = pd.DataFrame(attendance_data)

attendance_df.columns = attendance_df.columns.str.strip()
attendance_df["Date"] = pd.to_datetime(attendance_df["Date"], errors="coerce")

# =========================================================
# 🔥 AUTO REGISTER FIRST VISIT
# =========================================================
today = datetime.now().strftime("%Y-%m-%d")

for _, member in df.iterrows():

    member_id = str(member["MemberID"])

    existing = attendance_df[
        attendance_df["MemberID"] == member_id
    ]

    if existing.empty:

        row = [
            today,
            datetime.now().strftime("%H:%M"),
            "Auto Registration",
            member_id,
            member["First Name"] + " " + member["Surname"],
            "First Visit"
        ]

        attendance_sheet.append_row(row)

# =========================================================

# ----------------------------
# FILTER BY CHURCH
# ----------------------------
user_church = st.session_state.get("church")

if user_church:
    df = df[df["Branch"] == user_church]
else:
    df = pd.DataFrame()

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

province = st.sidebar.multiselect(
    "Province",
    options=df["Province"].dropna().unique(),
    default=df["Province"].dropna().unique()
)

gender = st.sidebar.multiselect(
    "Gender",
    options=df["Gender"].dropna().unique(),
    default=df["Gender"].dropna().unique()
)

filtered_df = df[
    (df["Province"].isin(province)) &
    (df["Gender"].isin(gender))
]

# ----------------------------
# KPI SECTION
# ----------------------------
col1, col2, col3, col4 = st.columns(4)

total_members = len(filtered_df)
avg_age = filtered_df["Age"].mean()

male = len(filtered_df[filtered_df["Gender"] == "Male"])
employment_rate = (
    len(filtered_df[filtered_df["Employment Status"] == "Employed"])
    / total_members * 100 if total_members > 0 else 0
)

col1.metric("👥 Total Members", total_members)
col2.metric("📊 Avg Age", round(avg_age, 1) if pd.notnull(avg_age) else 0)
col3.metric("👨 Male", male)
col4.metric("💼 Employed %", f"{round(employment_rate,1)}%")

# ----------------------------
# ATTENDANCE DASHBOARD
# ----------------------------
st.title("📊 Attendance Dashboard")

selected_service = st.selectbox(
    "Filter by Service",
    ["All"] + list(attendance_df["Service"].dropna().unique())
)

if selected_service != "All":
    attendance_df = attendance_df[attendance_df["Service"] == selected_service]

st.subheader("📈 Daily Attendance")
st.line_chart(attendance_df.groupby("Date").size())

st.subheader("⛪ Attendance by Service")
st.bar_chart(attendance_df["Service"].value_counts())

st.subheader("👥 Member Status")
st.bar_chart(attendance_df["Status"].value_counts())

st.subheader("🏆 Top Members")
st.bar_chart(attendance_df["Name"].value_counts().head(5))

attendance_df["Hour"] = attendance_df["Time"].str[:2]

st.subheader("⏰ Check-in Times")
st.bar_chart(attendance_df["Hour"].value_counts().sort_index())

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
