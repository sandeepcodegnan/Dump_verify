"""
Flask RESTful API for WhatsApp status checking and synchronization
"""
from flask import request
from flask_restful import Resource
from web.Exam.exam_central_db import db


class WhatsAppStatusAPI(Resource):
    def get(self):
        """
        Get WhatsApp delivery status from parent_message_status
        
        Query parameters:
        - report_type: weekly/monthly (required)
        - period_id: YYYY-MM-DD_to_YYYY-MM-DD (optional)
        - location: centre-name (optional)
        - batch: BATCHCODE (optional)
        """
        try:
            report_type = request.args.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            
            # Get period_id
            period_id = request.args.get("period_id")
            if not period_id:
                from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
                start_date, end_date = get_report_config(report_type)["date_calculator"]()
                period_id = f"{start_date}_to_{end_date}"
            
            location = request.args.get("location")
            batch = request.args.get("batch")
            
            # Get delivery status from parent_message_status
            query = {"period_id": period_id, "report_type": report_type}
            if location:
                query["location"] = location
                
            delivery_docs = list(db["parent_message_status"].find(query))
            
            if not delivery_docs:
                return {"success": False, "message": "No delivery data found"}, 404
            
            result = {
                "success": True,
                "period_id": period_id,
                "report_type": report_type,
                "delivery_data": delivery_docs
            }
            
            return result, 200
                
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500
    
