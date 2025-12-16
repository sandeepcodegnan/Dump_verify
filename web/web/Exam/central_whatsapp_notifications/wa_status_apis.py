from flask import request, jsonify
from flask_restful import Resource
import logging
import re
from web.Exam.central_whatsapp_notifications.helpers import extract_required
from web.Exam.central_whatsapp_notifications.wa_collections import wa_parent_collection, wa_examiner_collection
from web.Exam.central_whatsapp_notifications.log_records import SP_Weekly_Report, Daily_Exam_Notify
from web.Exam.central_whatsapp_notifications.async_processor import webhook_processor

logger = logging.getLogger(__name__)


log_weekly_wa_status = SP_Weekly_Report(wa_parent_collection)
log_daily_exam_wa_status = Daily_Exam_Notify(wa_examiner_collection)



class WaDailyExamDelivery(Resource):

    def post(self):
        try:
            payload = request.get_json(force=True)

            if not payload:
                logger.error("WaDailyExamDelivery: Empty payload received")
                return {"success": False, "error": "Empty payload"}, 400
            
            # Quick validation
            info = extract_required(payload, purpose="Daily_Exam")
            if not info.get("id") or not info.get("batch") or not info.get("date"):
                return {"success": False, "error": "Missing required fields"}, 400
            
            # Queue for async processing
            if webhook_processor.queue_exam_update(payload):
                return {"success": True, "queued": True}, 202
            else:
                return {"success": False, "error": "Queue full"}, 503
            
        except Exception as e:
            logger.error(f"Error in WaDailyExamDelivery: {str(e)}", exc_info=True)
            return {"success": False, "error": "Internal server error"}, 500





class WaParentStatusDelivery(Resource):
    def _filter_docs_by_batch(self, docs, batch):
        """Filter documents by specific batch"""
        filtered_docs = []
        for doc in docs:
            if "batches" in doc and batch in doc["batches"]:
                filtered_doc = {
                    "period_id": doc.get("period_id", doc.get("weekId")),
                    "location": doc["location"],
                    "report_type": doc.get("report_type", "weekly"),
                    "batches": {batch: doc["batches"][batch]}
                }
                filtered_docs.append(filtered_doc)
        return filtered_docs
    
    def get(self):
        period_id = request.args.get("period_id") or request.args.get("weekId")
        location = request.args.get("location")
        batch = request.args.get("batch")
        report_type = request.args.get("report_type", "weekly")
        
        if not period_id:
            return {"success": False, "error": "Missing period_id"}, 400
        
        # Sanitize inputs
        period_id = str(period_id)[:50] if period_id else None
        report_type = str(report_type)[:20] if report_type else "weekly"
        
        query = {"period_id": period_id, "report_type": report_type}
        if location:
            sanitized_location = re.escape(str(location)[:50])
            query["location"] = {"$regex": f"^{sanitized_location}$", "$options": "i"}
            
        try:
            docs = list(wa_parent_collection.find(query, {"_id": 0}))
            
            if batch:
                docs = self._filter_docs_by_batch(docs, str(batch)[:20])
            
            return jsonify(docs)
            
        except Exception as e:
            logger.error(f"Error in WaParentStatusDelivery GET: {str(e)}")
            return {"success": False, "error": str(e)}, 500

    def post(self):
        try:
            payload = request.get_json(force=True)
            #import json
            #print(json.dumps(payload, indent=4))
            logger.info(f"WaParentStatusDelivery: Received request - ID: {payload.get('id') if payload else 'None'}")
            
            if not payload:
                logger.error("WaParentStatusDelivery: Empty payload received")
                return {"success": False, "error": "Empty payload"}, 400
            
            # Extract report type from payload
            cf_map = {cf["name"]: cf["value"] for cf in payload.get("custom_fields", [])}
            report_type = cf_map.get("SP_ReportType") or "weekly"  # Default to weekly
            
            # Quick validation
            info = extract_required(payload, purpose=f"{report_type.title()}_Report")
            if not info.get("id") or not (info.get("period_id") or info.get("weekId")):
                return {"success": False, "error": "Missing required fields"}, 400
            
            # Queue for async processing
            if webhook_processor.queue_parent_update(payload):
                return {"success": True, "queued": True}, 202
            else:
                return {"success": False, "error": "Queue full"}, 503
                
        except Exception as e:
            logger.error(f"Error in WaParentStatusDelivery: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500