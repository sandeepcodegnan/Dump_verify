from web.Exam.Parent_Reports.logging_logs.log_config import get_logger
from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.date_utils import get_current_week_dates, get_current_month_dates

logger = get_logger("config.report_config")

# Report configurations
REPORT_CONFIGS = {
    "weekly": {
        "id_field": "weekId",
        "title": "Weekly Report",
        "date_calculator": get_current_week_dates,
        "collection": "parent_whatapp_report",
        "status_collection": "parent_report_status",
        "error_collection": "parent_error_logs",
        "success_collection": "parent_success_logs"
    },
    "monthly": {
        "id_field": "monthId", 
        "title": "Monthly Report",
        "date_calculator": get_current_month_dates,
        "collection": "parent_whatapp_report",
        "status_collection": "parent_report_status",
        "error_collection": "parent_error_logs",
        "success_collection": "parent_success_logs"
    }
}

def get_report_config(report_type):
    """Get configuration for specified report type"""
    if report_type not in REPORT_CONFIGS:
        raise ValueError(f"Invalid report type: {report_type}")
    return REPORT_CONFIGS[report_type]

def get_period_id(report_type, start_date=None, end_date=None):
    """Get period ID for the report type"""
    config = get_report_config(report_type)
    
    if start_date and end_date:
        return f"{start_date}_to_{end_date}"
    
    start_date, end_date = config["date_calculator"]()
    return f"{start_date}_to_{end_date}"