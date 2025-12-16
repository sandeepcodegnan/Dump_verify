"""Date Range Utilities - Week and Month Implementation"""
from datetime import datetime, timedelta

def validate_weekday_only(date_str: str, exam_type: str) -> None:
    """Validate that exam is scheduled on Monday-Saturday only
    
    Used by: Daily-Exam (blocks Sunday scheduling)
    
    Args:
        date_str: Date in YYYY-MM-DD format
        exam_type: Type of exam (e.g., "Daily-Exam")
    
    Raises:
        ValueError: If date falls on Sunday
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    if date.weekday() == 6:  # 6=Sunday
        raise ValueError(f"{exam_type} can only be conducted on Monday-Saturday")

def get_week_range(date_str: str) -> tuple:
    """Get Monday to Saturday range for given date
    
    Used by: Weekly-Exam (gets curriculum data for entire week)
    
    Args:
        date_str: Date in YYYY-MM-DD format (e.g., "2025-10-03")
    
    Returns:
        tuple: (start_date_str, end_date_str) - Monday to Saturday of that week
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Get Monday of the week (weekday 0=Monday, 6=Sunday)
    monday = date - timedelta(days=date.weekday())
    
    # Get Saturday of the week
    saturday = monday + timedelta(days=5)
    
    return monday.strftime("%Y-%m-%d"), saturday.strftime("%Y-%m-%d")

def get_month_range(date_str: str) -> tuple:
    """Get first to last day range for given month
    
    Used by: Monthly-Exam (gets curriculum data for entire month)
    
    Args:
        date_str: Date in YYYY-MM-DD format (e.g., "2025-10-15")
    
    Returns:
        tuple: (start_date_str, end_date_str) - First to last day of that month
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Get first day of the month
    first_day = date.replace(day=1)
    
    # Get last day of the month
    if date.month == 12:
        last_day = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
    
    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")