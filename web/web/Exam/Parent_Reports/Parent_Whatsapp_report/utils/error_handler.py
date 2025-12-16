"""
Centralized error handling
"""

class ErrorHandler:
    @staticmethod
    def handle_batch_error(e, batch_info, tracker):
        """Handle batch processing errors consistently"""
        batch_name = batch_info.get('Batch', 'Unknown')
        location_name = batch_info.get('location', 'Unknown')
        
        print(f"  Error: {batch_name} - {str(e)}")
        
        # Track error in timeline
        tracker.add_error(str(e), location=location_name, batch=batch_name)
        
        # Create error result
        return {
            "batch_info": batch_info,
            "success": False,
            "error": str(e),
            "status": "ERROR",
            "processed": 0,
            "time": 0
        }
    
    @staticmethod
    def create_error_stats(error_msg):
        """Create consistent error stats"""
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import create_stats_object, create_batch_stats_object
        
        pdf_stats = create_stats_object(
            status="ERROR",
            success=0,
            error=1,
            skipped=0,
            time_s=0,
            message=error_msg
        )
        
        batch_stats = create_batch_stats_object(
            status="ERROR",
            total=0,
            pdf_completed=0,
            whatsapp_completed=0,
            skipped=0,
            time_s=0,
            message=error_msg
        )
        
        return pdf_stats, batch_stats