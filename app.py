import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Intelligence System", layout="wide")

# ----------------------------
# GOOGLE SHEETS CONNECTION (SECRETS)
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
    users_sheet = client.open("ChurchApp").worksheet("Users")
    users_data = users_sheet.get_all_records()
    return pd.DataFrame(users_data)

def login():

    # Load users (THIS WAS MISSING)
    df = load_users()

    # Get user input
    input_email = st.text_input("Email")
    input_password = st.text_input("Password", type="password")

    if st.button("Login"):

        # Prevent empty inputs
        if not input_email or not input_password:
            st.warning("Please enter email and password")
            return

        # Clean inputs
        email = input_email.strip().lower()
        password = input_password.strip()

        # Clean dataframe
        df.columns = [str(col).strip().lower() for col in df.columns]

        df['email'] = df['email'].astype(str).str.strip().str.lower()
        df['password'] = df['password'].astype(str).str.strip()

        # Check user
        user = df[(df['email'] == email) & (df['password'] == password)]

        if not user.empty:
            st.session_state["logged_in"] = True
            st.session_state["church"] = user.iloc[0]["church"]  # ✅ IMPORTANT
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")
# ----------------------------
# MAIN DASHBOARD
# ----------------------------
st.title("⛪ Church Member Dashboard")

# ----------------------------
# LOAD MEMBER DATA
# ----------------------------
sheet = client.open("ChurchApp").worksheet("Members")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ----------------------------
# CLEAN DATA
# ----------------------------
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
# FILTER BY LOGGED-IN CHURCH
# ----------------------------
user_church = st.session_state.get("church")
#user_church = st.session_state["church"]
df = df[df["Branch"] == user_church]

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

# Apply filters
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
female = len(filtered_df[filtered_df["Gender"] == "Female"])

employment_rate = (
    len(filtered_df[filtered_df["Employment Status"] == "Employed"])
    / total_members * 100 if total_members > 0 else 0
)

col1.metric("👥 Total Members", total_members)
col2.metric("📊 Avg Age", round(avg_age, 1) if pd.notnull(avg_age) else 0)
col3.metric("👨 Male", male)
col4.metric("💼 Employed %", f"{round(employment_rate,1)}%")

# ----------------------------
# TABS
# ----------------------------
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Growth", "📋 Members"])

# ----------------------------
# OVERVIEW
# ----------------------------
with tab1:
    col1, col2 = st.columns(2)

    col1.subheader("Members by Province")
    col1.bar_chart(filtered_df["Province"].value_counts())

    col2.subheader("Members by Branch")
    col2.bar_chart(filtered_df["Branch"].value_counts())

    st.subheader("Gender Distribution")
    st.bar_chart(filtered_df["Gender"].value_counts())

    st.subheader("Employment Status")
    st.bar_chart(filtered_df["Employment Status"].value_counts())

    st.subheader("Age Distribution")
    st.bar_chart(filtered_df["Age"].value_counts().sort_index())

# ----------------------------
# GROWTH TRACKING
# ----------------------------
with tab2:
    st.subheader("📈 Church Growth Over Time")

    growth = filtered_df.copy()
    growth["Date"] = growth["Timestamp"].dt.date

    daily_growth = growth.groupby("Date").size()
    st.line_chart(daily_growth)

    growth["Month"] = growth["Timestamp"].dt.to_period("M")
    monthly_growth = growth.groupby("Month").size()

    st.subheader("Monthly Growth")
    st.bar_chart(monthly_growth)

# ----------------------------
# MEMBER TABLE
# ----------------------------
with tab3:
    st.subheader("📋 Member List")

    st.dataframe(filtered_df)

    st.download_button(
        "⬇ Download Data",
        filtered_df.to_csv(index=False),
        "church_members.csv"
    )

# ----------------------------
# LOGOUT BUTTON
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear() 
    st.rerun()                
