"""
Centralized tracker management to eliminate DRY violations
"""
from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker, create_stats_object, create_batch_stats_object


class TrackerManager:
    @staticmethod
    def initialize_tracker(report_type, period_id=None):
        """Initialize tracker with common setup"""
        # Determine period_id if not provided
        if not period_id:
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
            start_date, end_date = get_report_config(report_type)["date_calculator"]()
            period_id = f"{start_date}_to_{end_date}"
        
        tracker = ReportStatusTracker(report_type, period_id)
        tracker.initialize_status()
        
        # Set global status to PROCESSING
        processing_stats = create_stats_object(
            status="PROCESSING",
            success=0,
            error=0,
            skipped=0,
            time_s=0.0,
            message="Processing in progress..."
        )
        
        processing_batch_stats = create_batch_stats_object(
            status="PROCESSING",
            total=0,
            pdf_completed=0,
            whatsapp_completed=0,
            skipped=0,
            time_s=0.0,
            message="Batch processing in progress..."
        )
        
        tracker.update_global_status(pdf_stats=processing_stats, batch_stats=processing_batch_stats)
        
        return tracker, period_id
    
    @staticmethod
    def create_batch_stats_from_result(result):
        """Create batch stats from processing result"""
        status = result.get("status", "UNKNOWN")
        students_processed = result.get("processed", 0)
        processing_time = result.get("time", 0)
        
        return create_batch_stats_object(
            status=status,
            total=0,  # Don't increment total for individual batches
            pdf_completed=1 if status == "COMPLETED" else 0,
            whatsapp_completed=0,  # Will be updated when WhatsApp is implemented
            skipped=1 if status == "SKIPPED" else 0,
            time_s=processing_time,
            message=result.get("message", "")
        )
    
    @staticmethod
    def create_pdf_stats_from_result(result):
        """Create PDF stats from processing result"""
        status = result.get("status", "UNKNOWN")
        students_processed = result.get("processed", 0)
        processing_time = result.get("time", 0)
        
        return create_stats_object(
            status=status,
            success=students_processed if status == "COMPLETED" else 0,
            error=0,  # PDF-level errors (not batch errors)
            skipped=students_processed if status == "SKIPPED" else 0,
            time_s=processing_time,
            message=result.get("message", "")
        )