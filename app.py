# ----------------------------
# LOAD attendance sheet
# ----------------------------
attendance_sheet = client.open("ChurchApp").worksheet("Attendance")
attendance_data = attendance_sheet.get_all_records()
attendance_df = pd.DataFrame(attendance_data)

attendance_df.columns = attendance_df.columns.str.strip()
attendance_df["Date"] = pd.to_datetime(attendance_df["Date"], errors="coerce")

# =========================================================
# 🔥 AUTO REGISTER FIRST VISIT (NEW CODE ADDED)
# =========================================================
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")

for _, member in df.iterrows():

    member_id = str(member["MemberID"])

    # Check if member already exists in attendance
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
