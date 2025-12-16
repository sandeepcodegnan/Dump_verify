from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  


def auto_format_datetime(dt_input):
    """Automatically detect datetime type and convert to 'YYYY-MM-DD HH:MM:SS' format."""
    if dt_input is None:
        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')
    
    # If already a string in correct format, return as-is
    if isinstance(dt_input, str) and len(dt_input) == 19:
        try:
            datetime.fromisoformat(dt_input.replace(' ', 'T'))
            return dt_input
        except ValueError:
            pass
    
    # If datetime object
    if isinstance(dt_input, datetime):
        return dt_input.strftime('%Y-%m-%d %H:%M:%S')
    
    # If epoch timestamp (int or float)
    if isinstance(dt_input, (int, float)):
        try:
            # Handle milliseconds - 1e12 represents timestamp boundary (year 2001)
            if dt_input > 1e12:
                dt_input = dt_input / 1000.0
            return datetime.fromtimestamp(dt_input).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            pass
    
    # If string timestamp
    if isinstance(dt_input, str):
        try:
            # Try epoch timestamp
            ts = float(dt_input)
            # 1e12 represents timestamp boundary (year 2001) to distinguish seconds vs milliseconds
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            pass
        
        # Try HTTP date format
        try:
            dt_gmt = datetime.strptime(dt_input, '%a, %d %b %Y %H:%M:%S GMT')
            dt_gmt = dt_gmt.replace(tzinfo=ZoneInfo("UTC"))
            dt_ist = dt_gmt.astimezone(ZoneInfo("Asia/Kolkata"))
            return dt_ist.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    # Fallback to current time
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')


def fmt_datetime(raw):
    """Convert epoch-ms string to 'YYYY-MM-DD HH:MM:SS', or return raw on failure."""
    try:
        ts = int(raw) / 1000.0
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return raw or None

def fmt_last_delivered(raw):
    """
    - "-1" → keep "Delivery Failed"
    - "0"  → "Delivery Pending"
    - otherwise → human-readable timestamp
    """
    if str(raw) == "-1":
        return "Delivery Failed"
    if str(raw) == "0":
        return "Delivery Pending"
    return fmt_datetime(raw)

def fmt_optional(raw):
    """
    - "0" → "Not Available"
    - otherwise → human-readable timestamp
    """
    if str(raw) == "0":
        return "Not Available"
    return fmt_datetime(raw)

def convert_http_date(http_date: str) -> str:
    """Legacy function - use auto_format_datetime instead."""
    return auto_format_datetime(http_date)


def extract_required(data: dict, purpose: str = None) -> dict:
    """
    Extracts key identifiers and timestamps from input data.

    Parameters:
    - data (dict): Input data containing user/session metadata.
    - purpose (str, optional): Reserved for future filtering or formatting logic.

    Returns:
    - dict: Dictionary with selected and formatted fields.
    """
    cf_map = { cf["name"]: cf["value"] for cf in data.get("custom_fields", []) }
    
    info = {
        "id": data.get("id"),
        "last_sent": fmt_optional(data.get("last_sent")),
        "last_delivered": fmt_last_delivered(data.get("last_delivered")),
        "last_seen": fmt_optional(data.get("last_seen")),
        "last_interaction": fmt_optional(data.get("last_interaction")),
    }
    
    # Auto-detect purpose if not provided
    if purpose is None:
        # Check for explicit report type first
        if "SP_ReportType" in cf_map:
            report_type = cf_map["SP_ReportType"].lower()
            if report_type == "weekly":
                purpose = "Weekly_Report"
            elif report_type == "monthly":
                purpose = "Monthly_Report"
        # Check for weekly report fields
        elif ("SP_WReport_FromDt" in cf_map or "SP_WReport_ToDt" in cf_map or 
              "SP_WeeklyReport_PDF" in cf_map or "SP_Parent_Weekly" in cf_map or
              ("SP_WReport_FromDt" in cf_map and "SP_WReport_ToDt" in cf_map and 
               (lambda: (datetime.strptime(cf_map["SP_WReport_ToDt"], "%Y-%m-%d") - datetime.strptime(cf_map["SP_WReport_FromDt"], "%Y-%m-%d")).days == 5 and 
                        (datetime.strptime(cf_map["SP_WReport_ToDt"], "%Y-%m-%d") + timedelta(days=1)).weekday() == 6)())):
            purpose = "Weekly_Report"
        # Check for monthly report fields
        elif ("SP_MReport_FromDt" in cf_map or "SP_MReport_ToDt" in cf_map or 
              "SP_MonthlyReport_PDF" in cf_map or "SP_Parent_Monthly" in cf_map or
              ("SP_MReport_FromDt" in cf_map and "SP_MReport_ToDt" in cf_map and 
               (lambda: (lambda from_dt, to_dt: from_dt.day == 1 and to_dt.day == (to_dt.replace(month=to_dt.month+1, day=1) - timedelta(days=1)).day and from_dt.month == to_dt.month)
                (datetime.strptime(cf_map["SP_MReport_FromDt"], "%Y-%m-%d"), datetime.strptime(cf_map["SP_MReport_ToDt"], "%Y-%m-%d")))())):
            purpose = "Monthly_Report"
        # Check for daily exam fields
        elif "SP_ExamDt" in cf_map or "SP_ExamBatch" in cf_map or "SP_StudentId" in cf_map:
            purpose = "Daily_Exam"
        
        
    
    if purpose == "Weekly_Report":
        info["batch"]    = cf_map.get("SP_Batch")
        from_dt = cf_map.get("SP_WReport_FromDt")
        to_dt   = cf_map.get("SP_WReport_ToDt")
        info["period_id"] = cf_map.get("SP_PeriodId") or (f"{from_dt}_to_{to_dt}" if from_dt and to_dt else None)
        info["weekId"]   = info["period_id"]  # Backward compatibility
        info["location"] = cf_map.get("SP_Location")
        info["report_type"] = "weekly"
    elif purpose == "Monthly_Report":
        info["batch"]    = cf_map.get("SP_Batch")
        from_dt = cf_map.get("SP_MReport_FromDt")
        to_dt   = cf_map.get("SP_MReport_ToDt")
        info["period_id"] = cf_map.get("SP_PeriodId") or (f"{from_dt}_to_{to_dt}" if from_dt and to_dt else None)
        info["location"] = cf_map.get("SP_Location")
        info["report_type"] = "monthly"
    elif purpose == "Daily_Exam":
        info["Stuid"]    = cf_map.get("SP_StudentId")
        info['date'] = cf_map.get("SP_ExamDt")
        info['batch'] = cf_map.get("SP_ExamBatch")
    
        
        

    return info
