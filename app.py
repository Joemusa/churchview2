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
# CUSTOM STYLING
# ----------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: white;
    }
    .sub-title {
        color: #666666;
        font-size: 16px;
        margin-bottom: 1.2rem;
    }
    .kpi-card {
        border: 1px solid #d9d9d9;
        border-radius: 14px;
        padding: 14px 12px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        color: #1f1f1f;
    }
    .kpi-title {
        font-size: 14px;
        color: #555555;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        margin-top: 6px;
        color: #111111;
    }
    .chart-card {
        border: 1px solid #d9d9d9;
        border-radius: 16px;
        padding: 12px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 14px;
    }
    .login-card {
        max-width: 420px;
        margin: 60px auto;
        border: 1px solid #d9d9d9;
        border-radius: 18px;
        padding: 28px;
        background: white;
        box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# SIMPLE LOGIN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

APP_USERNAME = st.secrets.get("dashboard_username", "admin")
APP_PASSWORD = st.secrets.get("dashboard_password", "admin123")

if not st.session_state.logged_in:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("<div class='main-title'>🔐 Login</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Church Executive Dashboard</div>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect username or password")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

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
tithing = pd.DataFrame(client.open("ChurchApp").worksheet("Tithing").get_all_records())

if not members.empty:
    members.columns = members.columns.str.strip()

if not attendance.empty:
    attendance.columns = attendance.columns.str.strip()

if not tithing.empty:
    tithing.columns = tithing.columns.str.strip()
    tithing["Amount"] = pd.to_numeric(tithing["Amount"], errors="coerce")
    

members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Employment Status?": "Employment Status",
    "Cellphone?": "Cellphone"
})

# ----------------------------
# ENSURE EXPECTED COLUMNS
# ----------------------------
for col in ["Gender", "Province", "Region", "Employment Status", "Branch", "Age", "MemberID", "Leader", "First Name", "Surname", "Cellphone", "Birth Month", "Birth Day"]:
    if col not in members.columns:
        members[col] = ""

for col in ["Date", "Service", "MemberID", "Name", "Status"]:
    if col not in attendance.columns:
        attendance[col] = ""
        
for col in ["Date","Name", "Surname", "Amount", "Cellphone", "MemberID"]:
    if col not in tithing.columns:
        tithing[col] = ""


if "Timestamp" not in members.columns:
    members["Timestamp"] = pd.NaT

# ----------------------------
# STANDARDIZE KEYS
# ----------------------------
members["MemberID"] = members["MemberID"].astype(str).str.strip()
attendance["MemberID"] = attendance["MemberID"].astype(str).str.strip()

members["Full Name"] = (
    members["First Name"].astype(str).str.strip() + " " +
    members["Surname"].astype(str).str.strip()
).str.strip()

# Convert dates
members["Timestamp"] = pd.to_datetime(members["Timestamp"], errors="coerce")
attendance["Date"] = pd.to_datetime(attendance["Date"], errors="coerce")

# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("🔍 Filters")

gender_options = sorted([x for x in members["Gender"].dropna().unique() if str(x).strip() != ""])
leader_options = sorted([x for x in members["Leader"].dropna().unique() if str(x).strip() != ""])
province_options = sorted([x for x in members["Province"].dropna().unique() if str(x).strip() != ""])
region_options = sorted([x for x in members["Region"].dropna().unique() if str(x).strip() != ""])
employment_options = sorted([x for x in members["Employment Status"].dropna().unique() if str(x).strip() != ""])

gender = st.sidebar.multiselect("Gender", gender_options, default=gender_options)
leader = st.sidebar.multiselect("Leader", leader_options, default=leader_options)
province = st.sidebar.multiselect("Province", province_options, default=province_options)
region = st.sidebar.multiselect("Region", region_options, default=region_options)
employment = st.sidebar.multiselect("Employment Status", employment_options, default=employment_options)

date_range = st.sidebar.date_input("Select Date Range", [])

# ----------------------------
# FILTER DATA
# ----------------------------
members_f = members.copy()

if gender:
    members_f = members_f[members_f["Gender"].isin(gender)]
if leader:
    members_f = members_f[members_f["Leader"].isin(leader)]
if province:
    members_f = members_f[members_f["Province"].isin(province)]
if region:
    members_f = members_f[members_f["Region"].isin(region)]
if employment:
    members_f = members_f[members_f["Employment Status"].isin(employment)]

attendance_f = attendance.copy()

if "Date" in attendance_f.columns and len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    attendance_f = attendance_f[
        (attendance_f["Date"] >= start_date) &
        (attendance_f["Date"] <= end_date)
    ]

# ----------------------------
# DERIVED TABLES
# ----------------------------
new_visitors = attendance_f.copy()
if not new_visitors.empty:
    new_visitors["Status"] = new_visitors["Status"].astype(str).str.strip()
    new_visitors = new_visitors[
        new_visitors["Status"].isin(["First Visit", "Second Visit"])
    ].copy()

    new_visitors = new_visitors.sort_values("Date", ascending=False)

attended_member_ids = set(attendance_f["MemberID"].dropna().astype(str).str.strip())
members_not_attending = members_f[
    ~members_f["MemberID"].isin(attended_member_ids)
].copy()

# ----------------------------
# TITLE
# ----------------------------
st.markdown("<div class='main-title'>⛪ Church Executive Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Leadership view of members, attendance, visitors and non-attendance trends</div>", unsafe_allow_html=True)

# ----------------------------
# HELPERS
# ----------------------------
def show_kpi(title, value):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def clean_chart(fig):
    fig.update_layout(
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# ----------------------------
# KPI ROW
# ----------------------------
k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)

with k1:
    show_kpi("Total Members", members_f["MemberID"].nunique())

with k2:
    show_kpi("Male", len(members_f[members_f["Gender"] == "Male"]))

with k3:
    show_kpi("Female", len(members_f[members_f["Gender"] == "Female"]))

with k4:
    show_kpi("Present Members", len(attendance_f))

with k5:
    show_kpi("New Visitors", len(new_visitors))

with k6:
    show_kpi("Absent Members", len(members_not_attending))

with k7:
    show_kpi("Tithing Members", len(tithing))

with k8:
    total_tithing = tithing["Amount"].sum()
    show_kpi("Tithes", f"R {total_tithing:,.0f}")
# ----------------------------
# TABS
# ----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Dashboard",
    "📈 Growth",
    "👥 Total Members",
    "📋 Attendance",
    "🆕 New Visitors",
    "🚫 Not Attending",
    "💰 Tithing Members"
])

# ============================
# DASHBOARD
# ============================
with tab1:
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        gender_data = members_f["Gender"].dropna()
        gender_data = gender_data[gender_data.astype(str).str.strip() != ""]
        if not gender_data.empty:
            fig = px.pie(names=gender_data, values=[1] * len(gender_data))
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        emp = members_f["Employment Status"].value_counts().reset_index()
        emp.columns = ["Employment", "Count"]
        if not emp.empty:
            fig = px.bar(emp, x="Employment", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        age = members_f["Age"].value_counts().reset_index()
        age.columns = ["Age Group", "Count"]
        if not age.empty:
            fig = px.bar(age, x="Age Group", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    c4, c5, c6, c7 = st.columns(4)

    with c4:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        prov = members_f["Province"].value_counts().reset_index()
        prov.columns = ["Province", "Count"]
        if not prov.empty:
            fig = px.bar(prov, x="Province", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    with c5:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        serv = attendance_f["Service"].value_counts().reset_index()
        serv.columns = ["Service", "Count"]
        if not serv.empty:
            fig = px.bar(serv, x="Service", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    with c6:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        reg = members_f["Region"].value_counts().reset_index()
        reg.columns = ["Region", "Count"]
        if not reg.empty:
            fig = px.bar(reg, x="Region", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

    with c7:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        br = members_f["Branch"].value_counts().reset_index()
        br.columns = ["Branch", "Count"]
        if not br.empty:
            fig = px.bar(br, x="Branch", y="Count", text="Count")
            fig.update_traces(textposition="outside")
            st.plotly_chart(clean_chart(fig), use_container_width=True)
        else:
            st.info("No data available")
        st.markdown('</div>', unsafe_allow_html=True)

# ============================
# GROWTH
# ============================
with tab2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)

    mem_base = members.dropna(subset=["Timestamp"]).copy()
    att_base = attendance.dropna(subset=["Date"]).copy()

    mem_growth = mem_base.groupby(mem_base["Timestamp"].dt.date).size().reset_index(name="Members")
    mem_growth = mem_growth.rename(columns={"Timestamp": "Date"})

    att_growth = att_base.groupby(att_base["Date"].dt.date).size().reset_index(name="Attendance")
    att_growth = att_growth.rename(columns={"Date": "Date"})

    growth = pd.merge(mem_growth, att_growth, on="Date", how="outer").fillna(0)

    if not growth.empty:
        fig = px.line(growth, x="Date", y=["Members", "Attendance"], markers=True)
        st.plotly_chart(clean_chart(fig), use_container_width=True)
    else:
        st.info("No growth data available")

    st.markdown('</div>', unsafe_allow_html=True)

# ============================
# MEMBERS TABLE
# ============================
with tab3:
    st.subheader("Members Table")
    st.dataframe(members_f, use_container_width=True)

    st.download_button(
        "⬇ Export Members",
        members_f.to_csv(index=False),
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

# ============================
# NEW VISITORS TABLE
# ============================
with tab5:
    st.subheader("New Visitors")
    st.dataframe(new_visitors, use_container_width=True)

    st.download_button(
        "⬇ Export New Visitors",
        new_visitors.to_csv(index=False),
        "new_visitors.csv"
    )

# ============================
# MEMBERS NOT ATTENDING
# ============================
with tab6:
    st.subheader("Members Not Attending")
    st.dataframe(members_not_attending, use_container_width=True)

    st.download_button(
        "⬇ Export Members Not Attending",
        members_not_attending.to_csv(index=False),
        "members_not_attending.csv"
    )

# ============================
# TITHING MEMEBERS
# ============================
with tab7:
    st.subheader("Tithing Members")
    st.dataframe(tithing, use_container_width=True)

    st.download_button(
        "⬇ Export Tithing Members",
        tithing.to_csv(index=False),
        "tithing_members.csv"
    )
        
# ----------------------------
# LOGOUT
# ----------------------------
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()
