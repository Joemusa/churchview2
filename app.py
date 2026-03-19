import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Church Dashboard", layout="wide")

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
# LOGIN SYSTEM
# ----------------------------
def load_users():
    return pd.DataFrame(client.open("ChurchApp").worksheet("Users").get_all_records())

def login():
    users = load_users()
    users.columns = users.columns.str.strip().str.lower()

    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = users[
            (users["email"].str.strip().str.lower() == email.strip().lower()) &
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

# Clean columns
members.columns = members.columns.str.strip()
attendance.columns = attendance.columns.str.strip()

# Rename
members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Cellphone?": "Cellphone",
    "Employment Status?": "Employment Status"
})

# Convert dates
members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender = st.sidebar.multiselect(
    "Gender",
    members["Gender"].dropna().unique(),
    default=members["Gender"].dropna().unique()
)

province = st.sidebar.multiselect(
    "Province",
    members["Province"].dropna().unique(),
    default=members["Province"].dropna().unique()
)

region = st.sidebar.multiselect(
    "Region",
    members["Region"].dropna().unique(),
    default=members["Region"].dropna().unique()
)

employment = st.sidebar.multiselect(
    "Employment Status",
    members["Employment Status"].dropna().unique(),
    default=members["Employment Status"].dropna().unique()
)

# ----------------------------
# FILTER DATA
# ----------------------------
members_f = members[
    (members["Gender"].isin(gender)) &
    (members["Province"].isin(province)) &
    (members["Region"].isin(region)) &
    (members["Employment Status"].isin(employment))
]

attendance_f = attendance.copy()

if "Province" in attendance.columns:
    attendance_f = attendance_f[attendance_f["Province"].isin(province)]

if "Gender" in attendance.columns:
    attendance_f = attendance_f[attendance_f["Gender"].isin(gender)]

if "Region" in attendance.columns:
    attendance_f = attendance_f[attendance_f["Region"].isin(region)]

if "Employment Status" in attendance.columns:
    attendance_f = attendance_f[attendance_f["Employment Status"].isin(employment)]

# ----------------------------
# TITLE
# ----------------------------
st.title("⛪ Church Analytics Dashboard")

# ----------------------------
# KPI (ONE ROW - FILTERED)
# ----------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("👥 Members", members_f["MemberID"].nunique())
k2.metric("👨 Male", len(members_f[members_f["Gender"] == "Male"]))
k3.metric("👩 Female", len(members_f[members_f["Gender"] == "Female"]))
k4.metric("📍 Provinces", members_f["Province"].nunique())
k5.metric("📊 Attendance", len(attendance_f))
k6.metric("⛪ Services", attendance_f["Service"].nunique() if "Service" in attendance_f.columns else 0)

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

    # Top row
    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            px.pie(members_f, names="Gender", title="Gender Distribution"),
            use_container_width=True
        )

    with c2:
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment Status", "Count"]

        st.plotly_chart(
            px.bar(emp, x="Employment Status", y="Count", title="Employment"),
            use_container_width=True
        )

    # Second row (4 charts aligned)
    c3, c4, c5, c6 = st.columns(4)

    with c3:
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]

        st.plotly_chart(
            px.bar(prov, x="Province", y="Count", title="Province"),
            use_container_width=True
        )

    with c4:
        if "Service" in attendance_f.columns:
            serv = attendance_f["Service"].value_counts().reset_index()
            serv.columns = ["Service", "Count"]

            st.plotly_chart(
                px.bar(serv, x="Service", y="Count", title="Service Attendance"),
                use_container_width=True
            )

    with c5:
        reg = members_f["Region"].value_counts().reset_index()
        reg.columns = ["Region", "Count"]

        st.plotly_chart(
            px.bar(reg, x="Region", y="Count", title="Region"),
            use_container_width=True
        )

    with c6:
        br = members_f["Branch"].value_counts().reset_index()
        br.columns = ["Branch", "Count"]

        st.plotly_chart(
            px.bar(br, x="Branch", y="Count", title="Branch"),
            use_container_width=True
        )

# ============================
# GROWTH
# ============================
with tab2:

    mem_growth = members.groupby(members["Timestamp"].dt.date).size().reset_index(name="Members")
    mem_growth.columns = ["Date", "Members"]

    att_growth = attendance.groupby(attendance["Date"].dt.date).size().reset_index(name="Attendance")
    att_growth.columns = ["Date", "Attendance"]

    growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

    st.plotly_chart(
        px.line(growth, x="Date", y=["Members", "Attendance"], title="Growth Over Time"),
        use_container_width=True
    )

# ============================
# MEMBERS TABLE
# ============================
with tab3:

    st.subheader("Members Table")

    show_filtered = st.checkbox("Show filtered data only")

    if show_filtered:
        table = members_f
    else:
        table = members

    st.dataframe(table, use_container_width=True)

    st.download_button(
        "⬇ Export Members",
        table.to_csv(index=False),
        "members.csv"
    )

# ============================
# ATTENDANCE TABLE
# ============================
with tab4:

    st.subheader("Attendance Table")

    st.dataframe(attendance_f, use_container_width=True)

    st.download_button(
        "⬇ Export Attendance",
        attendance_f.to_csv(index=False),
        "attendance.csv"
    )

# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
