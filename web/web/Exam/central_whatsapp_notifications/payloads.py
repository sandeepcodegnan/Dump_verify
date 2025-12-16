import re

# ─── Helpers ─────────────────────────────────────────────────────────────────
def clean_phone(raw: str) -> str:
    """Return digits-only E.164 number; add +91 if exactly 10 digits."""
    if not raw:
        return ""
    digits = "".join(re.findall(r"\d", raw))
    if len(digits) == 10:
        digits = "91" + digits
    elif len(digits) < 10:
        return ""
    return digits.lstrip("+")


def SP_Payload(first_name, phone, pdf_url, from_dt, to_dt, location, student_name=None, batch=None, period_id=None, report_type="weekly"):
    """Create WhatsApp payload for parent reports (weekly/monthly)"""
    # Common payload structure
    base_payload = {
        "phone": phone,
        "first_name": first_name,
        "actions": [
            {"action": "set_field_value", "field_name": "role", "value": "Parent"},
            {"action": "set_field_value", "field_name": "SP_StName", "value": student_name},
            {"action": "set_field_value", "field_name": "SP_Location", "value": location},
            {"action": "set_field_value", "field_name": "SP_Batch", "value": batch},
            {"action": "set_field_value", "field_name": "SP_PeriodId", "value": period_id},
            {"action": "set_field_value", "field_name": "SP_ReportType", "value": report_type},
        ]
    }
    
    # Report-specific fields
    if report_type == "monthly":
        base_payload["actions"].extend([
            {"action": "add_tag", "tag_name": "SP_Parent_Monthly"},
            {"action": "set_field_value", "field_name": "SP_MonthlyReport_PDF", "value": pdf_url},
            {"action": "set_field_value", "field_name": "SP_MReport_FromDt", "value": from_dt},
            {"action": "set_field_value", "field_name": "SP_MReport_ToDt", "value": to_dt}
        ])
    else:
        base_payload["actions"].extend([
            {"action": "add_tag", "tag_name": "SP_Parent_Weekly"},
            {"action": "set_field_value", "field_name": "SP_WeeklyReport_PDF", "value": pdf_url},
            {"action": "set_field_value", "field_name": "SP_WReport_FromDt", "value": from_dt},
            {"action": "set_field_value", "field_name": "SP_WReport_ToDt", "value": to_dt}
        ])
    
    return base_payload


def Examiner_Payload(name, sid, phone, exam_name,
                 start_date, window_period, total_time,
                 subjects, batch, flow_id=None):

    phone = clean_phone(phone)
    if not phone:
        print(f"[SKIP] {sid} – invalid phone number")
        return
        
    payload = {
        "phone": phone,
        "first_name": name,
        "last_name": "",
        "gender": "male",
        "actions": [
            {"action":"add_tag", "tag_name":"SP_ExamOrderWindow"},
            {"action":"set_field_value", "field_name":"SP_StudentId",   "value": sid},
            {"action":"set_field_value", "field_name":"SP_ExamBatch",   "value": batch},
            {"action":"set_field_value", "field_name":"SP_ExamSub",     "value": subjects},
            {"action":"set_field_value", "field_name":"SP_ExamDayOrder","value": exam_name},
            {"action":"set_field_value", "field_name":"SP_ExamDt",      "value": start_date},
            {"action":"set_field_value", "field_name":"SP_ExamT",       "value": window_period},
            {"action":"set_field_value", "field_name":"SP_ExamDuration","value": str(total_time)}
        ]
    }
    if flow_id:
        payload["actions"].insert(0, {"action":"send_flow","flow_id": flow_id})
    return payload

def Admin_Payload(phone,name,date,greeting,m):

    payload = {
            "phone":      phone,
            "first_name": name,
            "actions": [
                {"action": "add_tag",         "tag_name": "SP_adminreports"},
                {"action": "set_field_value", "field_name": "SP_Report_Date",            "value": date},
                {"action": "set_field_value", "field_name": "SP_Greetings",              "value": greeting},
                {"action": "set_field_value", "field_name": "SP_locations_allocated",     "value": m["alloc_parts"]},
                {"action": "set_field_value", "field_name": "SP_total_allocated",         "value": str(m["total_alloc"])},
                {"action": "set_field_value", "field_name": "SP_locations_attempted",     "value": m["attempt_parts"]},
                {"action": "set_field_value", "field_name": "SP_locations_not_attempted", "value": m["non_attempt_parts"]},
                {"action": "set_field_value", "field_name": "SP_total_attempted",         "value": str(m["total_attempt"])},
                {"action": "set_field_value", "field_name": "SP_total_not_attempted",     "value": str(m["total_non_attempt"])},
            ],
        }
    return payload
