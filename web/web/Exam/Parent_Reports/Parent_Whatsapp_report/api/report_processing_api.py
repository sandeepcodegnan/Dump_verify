from flask import request
from flask_restful import Resource
from web.Exam.Parent_Reports.Parent_Whatsapp_report.services.report_processing_service import process_reports
from web.Exam.Parent_Reports.Parent_Whatsapp_report.async_processor import async_processor


class ReportProcessorAPI(Resource):
    def post(self):
        try:
            data = request.get_json(force=True)
            if not data:
                return {"success": False, "error": "No JSON data provided"}, 400
            report_type = data.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            batch = data.get("batch")
            location = data.get("location")
            if batch and not location:
                return {"success": False, "error": "batch parameter requires location to be specified"}, 400
            use_async = data.get("async", True)
            if use_async:
                task_id = async_processor.start_processing(
                    report_type=report_type,
                    location=location,
                    batch=batch,
                    force=data.get("force", False),
                    period_id=data.get("period_id"),
                    start_date=data.get("start_date"),
                    end_date=data.get("end_date")
                )
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "QUEUED",
                    "message": "Report processing started in background",
                    "status_url": f"/api/v1/reports-status/{task_id}"
                }, 202
            else:
                result = process_reports(
                    report_type=report_type,
                    location=location,
                    batch=batch,
                    force=data.get("force", False),
                    period_id=data.get("period_id"),
                    start_date=data.get("start_date"),
                    end_date=data.get("end_date")
                )
                return result, 200 if result["success"] else 400
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500

    def get(self):
        try:
            report_type = request.args.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            period_id = request.args.get("period_id")
            if not period_id:
                from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
                start_date, end_date = get_report_config(report_type)["date_calculator"]()
                period_id = f"{start_date}_to_{end_date}"
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker
            tracker = ReportStatusTracker(report_type, period_id)
            status = tracker.get_status()
            if not status:
                return {"success": False, "message": f"No status found for {period_id}"}, 404
            def convert_datetime(obj):
                if isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                elif hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                else:
                    return obj
            serializable_status = convert_datetime(status)
            return {"success": True, "period_id": period_id, "report_type": report_type, "status": serializable_status}, 200
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500
