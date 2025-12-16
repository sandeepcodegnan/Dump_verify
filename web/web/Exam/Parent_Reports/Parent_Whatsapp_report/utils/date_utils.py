from datetime import datetime, timedelta
from web.Exam.Parent_Reports.logging_logs.log_config import get_logger

logger = get_logger("utils.date_utils")

def get_current_week_dates():
    """Calculate the start (Monday) and end (Saturday) dates for the current week"""
    today = datetime.now()
    days_from_monday = today.weekday()
    monday = today - timedelta(days=days_from_monday)
    saturday = monday + timedelta(days=5)
    return monday.strftime("%Y-%m-%d"), saturday.strftime("%Y-%m-%d")

def get_current_month_dates():
    """Calculate start and end dates for previous month"""
    today = datetime.now()
    # Get first day of current month
    first_day_current = today.replace(day=1)
    # Get last day of previous month
    last_day_prev = first_day_current - timedelta(days=1)
    # Get first day of previous month
    first_day_prev = last_day_prev.replace(day=1)
    
    return first_day_prev.strftime("%Y-%m-%d"), last_day_prev.strftime("%Y-%m-%d")

def parse_period_id(period_id):
    """Parse period ID to get start and end dates"""
    try:
        start_str, end_str = period_id.split("_to_")
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")
        return start_dt, end_dt
    except ValueError:
        raise ValueError("Invalid period ID format (expected: YYYY-MM-DD_to_YYYY-MM-DD)")

def get_date_range_days(start_date, end_date):
    """Get list of dates between start and end date (inclusive)"""
    delta_days = (end_date - start_date).days + 1
    return [
        (start_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(delta_days)
    ]

def get_date_query_conditions(collection, date_field, start_dt, end_dt):
    """
    Determine the correct date query conditions based on the data type in the collection.
    Returns a query dict that works with the actual data format.
    """
    # Try with datetime objects first
    try:
        count = collection.count_documents({date_field: {"$gte": start_dt, "$lte": end_dt}})
        #logger.info(f"Found {count} records with datetime objects")
        if count > 0:
            return {date_field: {"$gte": start_dt, "$lte": end_dt}}
    except Exception as e:
        #logger.warning(f"Error with datetime query: {str(e)}")
        pass
    
    # Try with string format
    try:
        start_str = start_dt.strftime("%Y-%m-%d") if hasattr(start_dt, 'strftime') else start_dt
        end_str = end_dt.strftime("%Y-%m-%d") if hasattr(end_dt, 'strftime') else end_dt
        count = collection.count_documents({date_field: {"$gte": start_str, "$lte": end_str}})
        #logger.info(f"Found {count} records with string dates")
        if count > 0:
            return {date_field: {"$gte": start_str, "$lte": end_str}}
    except Exception as e:
        #logger.warning(f"Error with string date query: {str(e)}")
        pass
    
    # Try with ISODate string format
    try:
        start_iso = start_dt.isoformat() if hasattr(start_dt, 'isoformat') else start_dt
        end_iso = end_dt.isoformat() if hasattr(end_dt, 'isoformat') else end_dt
        count = collection.count_documents({date_field: {"$gte": start_iso, "$lte": end_iso}})
        #logger.info(f"Found {count} records with ISO date strings")
        if count > 0:
            return {date_field: {"$gte": start_iso, "$lte": end_iso}}
    except Exception as e:
        #logger.warning(f"Error with ISO date query: {str(e)}")
        pass
    
    # Default to original format
    #logger.warning(f"No matching date format found, using original format")
    return {date_field: {"$gte": start_dt, "$lte": end_dt}}