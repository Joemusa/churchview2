import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Church Executive Dashboard", layout="wide")

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
# FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender = st.sidebar.multiselect("Gender", members["Gender"].dropna().unique(), default=members["Gender"].dropna().unique())
province = st.sidebar.multiselect("Province", members["Province"].dropna().unique(), default=members["Province"].dropna().unique())
region = st.sidebar.multiselect("Region", members["Region"].dropna().unique(), default=members["Region"].dropna().unique())
employment = st.sidebar.multiselect("Employment Status", members["Employment Status"].dropna().unique(), default=members["Employment Status"].dropna().unique())

date_range = st.sidebar.date_input("Select Date Range", [])

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

if "Date" in attendance.columns and len(date_range) == 2:
    attendance_f = attendance_f[
        (attendance_f["Date"] >= pd.to_datetime(date_range[0])) &
        (attendance_f["Date"] <= pd.to_datetime(date_range[1]))
    ]

# ----------------------------
# KPI
# ----------------------------
st.title("⛪ Church Executive Dashboard")

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Members", members_f["MemberID"].nunique())
k2.metric("Male", len(members_f[members_f["Gender"] == "Male"]))
k3.metric("Female", len(members_f[members_f["Gender"] == "Female"]))
k4.metric("Provinces", members_f["Province"].nunique())
k5.metric("Attendance", len(attendance_f))
k6.metric("Services", attendance_f["Service"].nunique() if "Service" in attendance_f.columns else 0)

# ----------------------------
# CLEAN CHART STYLE
# ----------------------------
def clean_chart(fig):
    fig.update_layout(
        yaxis=dict(visible=False, showgrid=False),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

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

    # 🔥 ROW 1 (FIXED)
    c1, c2, c3 = st.columns(3)

    # PIE
    with c1:
        fig = px.pie(members_f, names="Gender")
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # EMPLOYMENT
    with c2:
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment", "Count"]
        fig = px.bar(emp, x="Employment", y="Count", text="Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(clean_chart(fig), use_container_width=True)

    # AGE
    with c3:
        age = members_f["Age"].value_counts().reset_index()
        age.columns = ["Age Group", "Count"]
        fig = px.bar(age, x="Age Group", y="Count", text="Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(clean_chart(fig), use_container_width=True)

    # 🔥 ROW 2
    c4, c5, c6, c7 = st.columns(4)

    with c4:
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]
        fig = px.bar(prov, x="Province", y="Count", text="Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(clean_chart(fig), use_container_width=True)

    with c5:
        if "Service" in attendance_f.columns:
            serv = attendance_f["Service"].value_counts().reset_index()
            serv.columns = ["Service", "Count"]
            fig = px.bar(serv, x="Service", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)

    with c6:
        reg = members_f["Region"].value_counts().reset_index()
        reg.columns = ["Region", "Count"]
        fig = px.bar(reg, x="Region", y="Count", text="Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(clean_chart(fig), use_container_width=True)

    with c7:
        br = members_f["Branch"].value_counts().reset_index()
        br.columns = ["Branch", "Count"]
        fig = px.bar(br, x="Branch", y="Count", text="Count")
        fig.update_traces(textposition="outside")
        st.plotly_chart(clean_chart(fig), use_container_width=True)

# ============================
# GROWTH
# ============================
with tab2:

    mem_growth = members.groupby(members["Timestamp"].dt.date).size().reset_index(name="Members")
    att_growth = attendance.groupby(attendance["Date"].dt.date).size().reset_index(name="Attendance")

    growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

    fig = px.line(growth, x="Date", y=["Members", "Attendance"], markers=True)
    fig.update_layout(
        yaxis=dict(visible=False, showgrid=False),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================
# MEMBERS TABLE
# ============================
with tab3:
    st.subheader("Members Table")
    st.dataframe(members, use_container_width=True)

    st.download_button(
        "⬇ Export Members",
        members.to_csv(index=False),
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
