"""Time utilities - DRY principle"""
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# Current IST time using for exam timestamps

def now_ist() -> datetime:
    return datetime.now(IST)

def parse_ist_datetime(date_str: str, time_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(f"{date_str}T{time_str}")
        return dt.replace(tzinfo=IST)
    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {e}")

def parse_date_safe(date_str: str) -> datetime:
    """Parse date with ISO format for performance"""
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%d")

def format_duration(seconds: int) -> str:
    if seconds < 0:
        return "00:00:00"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# Additional helper functions for time conversions for window time configurations

def time_to_seconds(time_obj) -> int:
    """Convert time object to seconds since midnight"""
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

def seconds_to_time_str(seconds: int) -> str:
    """Convert seconds since midnight to HH:MM format"""
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

def seconds_to_time_str_12hr(seconds: int) -> str:
    """Convert seconds since midnight to 12-hour format (h:MM AM/PM)"""
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if hours == 0:
        return f"12:{minutes:02d} AM"
    elif hours < 12:
        return f"{hours}:{minutes:02d} AM"
    elif hours == 12:
        return f"12:{minutes:02d} PM"
    else:
        return f"{hours - 12}:{minutes:02d} PM"

def calculate_duration(start_seconds: int, end_seconds: int) -> int:
    """Calculate duration between two time points in seconds"""
    return end_seconds - start_seconds

def parse_date_to_native(date_str: str) -> datetime:
    """Parse date string to native datetime object (ISO format)"""
    try:
        # Parse YYYY-MM-DD to native datetime with IST timezone
        dt = datetime.fromisoformat(date_str)
        return dt.replace(tzinfo=IST)
    except ValueError as e:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {e}")

def date_to_iso_string(date_obj: datetime) -> str:
    """Convert native datetime to ISO date string"""
    return date_obj.strftime("%Y-%m-%d")

def combine_date_time_native(date_obj: datetime, time_seconds: int) -> datetime:
    """Combine native date with time seconds to create full datetime"""
    hours, remainder = divmod(time_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return date_obj.replace(
        hour=hours, 
        minute=minutes, 
        second=seconds, 
        microsecond=0,
        tzinfo=IST
    )

def get_ist_timestamp() -> datetime:
    """Get current IST timestamp for exam status updates"""
    return now_ist()

def format_ist_timestamp(timestamp: datetime) -> str:
    """Format IST timestamp to readable string"""
    return timestamp.strftime("%Y-%m-%d %H:%M:%S IST")