import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import time

st.set_page_config(layout="centered")

st.title("⛪ Church Check-In")

# ----------------------------
# CONNECT TO GOOGLE SHEETS
# ----------------------------
client = gspread.service_account_from_dict(
    st.secrets["gcp_service_account"]
)

spreadsheet = client.open("ChurchApp")

members_sheet = spreadsheet.worksheet("Members")
attendance_sheet = spreadsheet.worksheet("Attendance")

# ----------------------------
# LOAD DATA
# ----------------------------
members = pd.DataFrame(members_sheet.get_all_records())
attendance = pd.DataFrame(attendance_sheet.get_all_records())

members.columns = members.columns.str.strip()
attendance.columns = attendance.columns.str.strip()

# Rename for consistency
members = members.rename(columns={
    "First Name?": "First Name",
    "Surname?": "Surname",
    "Cellphone?": "Cellphone",
    "Employment Status?": "Employment Status"
})

# ----------------------------
# SELECT SERVICE
# ----------------------------
service = st.selectbox(
    "Select Service",
    ["Sunday Service", "Youth Service", "Prayer Meeting", "Special Event"]
)

today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M")

# =========================================================
# 🔥 AUTO FIRST VISIT (GOOGLE FORM SUBMISSIONS)
# =========================================================
for _, member in members.iterrows():

    member_id = str(member["MemberID"])

    existing = attendance[
        attendance["MemberID"] == member_id
    ]

    if existing.empty:

        attendance_sheet.append_row([
            today,
            current_time,
            "Auto Registration",
            member_id,
            member["First Name"] + " " + member["Surname"],
            "First Visit",
            member.get("Province", ""),
            member.get("Branch", ""),
            member.get("Gender", ""),
            member.get("Region", ""),
            member.get("Employment Status", "")
        ])

# =========================================================
# 🔥 QR CODE CHECK-IN
# =========================================================
query_params = st.query_params
member_qr = query_params.get("member")

if member_qr:

    member = members[members["MemberID"] == member_qr]

    if not member.empty:

        member = member.iloc[0]

        # Prevent duplicate check-in for same service & day
        duplicate = attendance[
            (attendance["MemberID"] == member_qr) &
            (attendance["Date"] == today) &
            (attendance["Service"] == service)
        ]

        if not duplicate.empty:
            st.warning("Already checked in today")
            st.stop()

        # Visit count
        history = attendance[attendance["MemberID"] == member_qr]
        visits = len(history) + 1

        if visits == 1:
            status = "First Visit"
        elif visits == 2:
            status = "Second Visit"
        else:
            status = "Regular Member"

        attendance_sheet.append_row([
            today,
            current_time,
            service,
            member_qr,
            member["First Name"] + " " + member["Surname"],
            status,
            member.get("Province", ""),
            member.get("Branch", ""),
            member.get("Gender", ""),
            member.get("Region", ""),
            member.get("Employment Status", "")
        ])

        st.success(f"Welcome {member['First Name']} ({status})")
        time.sleep(2)
        st.rerun()

# =========================================================
# 🔥 4-DIGIT CHECK-IN
# =========================================================
digits = st.text_input("Enter last 4 digits of your phone")

if digits and len(digits) == 4:

    matches = members[members["Cellphone"].astype(str).str.endswith(digits)]

    if matches.empty:
        st.error("Member not found")
    else:
        matches["FullName"] = matches["First Name"] + " " + matches["Surname"]

        selected = st.selectbox("Select your name", matches["FullName"])

        if st.button("Confirm Check-In"):

            member = matches[matches["FullName"] == selected].iloc[0]
            member_id = str(member["MemberID"])

            # Prevent duplicates
            duplicate = attendance[
                (attendance["MemberID"] == member_id) &
                (attendance["Date"] == today) &
                (attendance["Service"] == service)
            ]

            if not duplicate.empty:
                st.warning("Already checked in today")
                st.stop()

            # Visit count
            history = attendance[attendance["MemberID"] == member_id]
            visits = len(history) + 1

            if visits == 1:
                status = "First Visit"
            elif visits == 2:
                status = "Second Visit"
            else:
                status = "Regular Member"

            attendance_sheet.append_row([
                today,
                current_time,
                service,
                member_id,
                member["First Name"] + " " + member["Surname"],
                status,
                member.get("Province", ""),
                member.get("Branch", ""),
                member.get("Gender", ""),
                member.get("Region", ""),
                member.get("Employment Status", "")
            ])

            st.success(f"Check-in successful ({status})")
            time.sleep(2)
            st.rerun()
