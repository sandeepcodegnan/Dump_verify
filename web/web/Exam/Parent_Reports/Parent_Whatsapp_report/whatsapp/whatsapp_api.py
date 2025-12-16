"""
Flask RESTful API for WhatsApp processing
"""
from flask import request
from flask_restful import Resource
from web.Exam.Parent_Reports.Parent_Whatsapp_report.whatsapp.whatsapp_processor import (
    process_whatsapp_reports,
    get_batches_ready_for_whatsapp
)
from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker, create_stats_object
from web.Exam.Parent_Reports.Parent_Whatsapp_report.async_processor import async_processor


class WhatsAppAPI(Resource):
    def post(self):
        """
        Send WhatsApp messages for completed PDF reports (Async)
        
        Expected JSON body:
        {
            "report_type": "weekly" or "monthly",     # required
            "period_id": "YYYY-MM-DD_to_YYYY-MM-DD", # optional
            "location": "centre-name",                # optional
            "batch": "BATCHCODE",                     # optional (requires location)
            "async": true/false                       # optional, default true
        }
        """
        try:
            data = request.get_json(force=True)
            if not data:
                return {"success": False, "error": "No JSON data provided"}, 400
            
            report_type = data.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            
            # Get period_id
            period_id = data.get("period_id")
            if not period_id:
                from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
                start_date, end_date = get_report_config(report_type)["date_calculator"]()
                period_id = f"{start_date}_to_{end_date}"
            
            location = data.get("location")
            batch = data.get("batch")
            
            # Validate batch parameter requires location
            if batch and not location:
                return {"success": False, "error": "batch parameter requires location to be specified"}, 400
            
            # Check if async processing requested (default: true)
            use_async = data.get("async", True)
            
            if use_async:
                # Start async WhatsApp processing
                task_id = async_processor.start_whatsapp_processing(
                    report_type=report_type,
                    period_id=period_id,
                    location=location,
                    batch=batch
                )
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "QUEUED",
                    "message": "WhatsApp processing started in background",
                    "status_url": f"/api/v1/reports-status/{task_id}"
                }, 202
            else:
                # Synchronous processing (backward compatibility)
                result = process_whatsapp_reports(
                    report_type=report_type,
                    period_id=period_id,
                    location=location,
                    batch=batch
                )
                
                return result, 200 if result["success"] else 400
                
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500
    
    def get(self):
        """
        Get batches ready for WhatsApp sending
        
        Query parameters:
        - report_type: weekly/monthly (required)
        - period_id: YYYY-MM-DD_to_YYYY-MM-DD (optional)
        """
        try:
            report_type = request.args.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            
            period_id = request.args.get("period_id")
            if not period_id:
                from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
                start_date, end_date = get_report_config(report_type)["date_calculator"]()
                period_id = f"{start_date}_to_{end_date}"
            
            ready_batches = get_batches_ready_for_whatsapp(period_id, report_type)
            
            return {
                "success": True,
                "period_id": period_id,
                "report_type": report_type,
                "ready_batches": len(ready_batches),
                "batches": ready_batches
            }, 200
            
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500