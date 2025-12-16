import logging
from web.Exam.central_whatsapp_notifications.helpers import fmt_optional, auto_format_datetime
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
from web.Exam.exam_central_db import whatsapp_stats_collection
import time
from pymongo.errors import DuplicateKeyError
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseNotificationHandler(ABC):
    """Base class for all notification handlers - implements common functionality"""
    MAX_RETRIES = 3
    
    def __init__(self, collection):
        self.col = collection
    
    def _validate_required_fields(self, info, required_fields):
        """Common validation logic"""
        for field in required_fields:
            if field not in info or info[field] is None:
                return {"success": False, "error": f"Missing required field: {field}"}
        return {"success": True}
    
    def _build_interaction_update_query(self, batch, updates):
        """Common update query builder"""
        update_query = {
            f"batches.{batch}.$[elem].last_sent": auto_format_datetime(updates.get("last_sent")),
            f"batches.{batch}.$[elem].last_delivered": auto_format_datetime(updates.get("last_delivered")),
            f"batches.{batch}.$[elem].last_seen": auto_format_datetime(updates.get("last_seen")),
            f"batches.{batch}.$[elem].last_interaction": auto_format_datetime(updates.get("last_interaction")),
            f"batches.{batch}.$[elem].updated_at": auto_format_datetime(None)
        }
        return {k: v for k, v in update_query.items() if v is not None}
    
    @abstractmethod
    def insert_or_update_details(self, info):
        pass
    
    @abstractmethod
    def update_interaction_fields(self, *args, **kwargs):
        pass


class SP_Weekly_Report(BaseNotificationHandler):
    """Handler for weekly reports with period-based structure"""
    
    def __init__(self, collection=None):
        super().__init__(collection if collection is not None else whatsapp_stats_collection)
    
    def insert_or_update_details(self, info):
        period_id = info.get("period_id")
        location = info.get("location")
        batch = info.get("batch")
        report_type = info.get("report_type", "weekly")

        validation = self._validate_required_fields(info, ["phone", "student_name", "s3_url", "sent"])
        if not validation["success"]:
            return validation

        details = {
            "id": info["phone"],
            "name": info["student_name"],
            "s3_url": info['s3_url'],
            "sent": auto_format_datetime(info['sent']),
            "last_sent": fmt_optional(0),
            "last_delivered": fmt_optional(0),
            "last_seen": fmt_optional(0),
            "last_interaction": fmt_optional(0),
            "updated_at": auto_format_datetime(None)
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                existing_doc = self.col.find_one(
                    {"period_id": period_id, "location": location, "report_type": report_type}
                )
                
                if existing_doc:
                    result = self.col.update_one(
                        {"_id": existing_doc["_id"]},
                        {
                            "$push": {f"batches.{batch}": details},
                            "$set": {"last_updated": auto_format_datetime(None)}
                        }
                    )
                else:
                    result = self.col.insert_one({
                        "period_id": period_id,
                        "location": location,
                        "report_type": report_type,
                        "created_at": auto_format_datetime(None),
                        "last_updated": auto_format_datetime(None),
                        "batches": {batch: [details]}
                    })
                
                return {"success": True, "modified_count": 1}
                
            except DuplicateKeyError:
                logger.warning(f"Duplicate key on insert (attempt {attempt+1}), retrying...")
                time.sleep(0.1)
            except Exception as e:
                logger.exception("Database update failed")
                return {"success": False, "error": str(e)}
                
        return {"success": False, "message": "Max retries exceeded"}

    def update_interaction_fields(self, period_id, location, batch, record_id, updates, report_type="weekly"):
        if not all([period_id, location, batch, record_id]):
            return {"success": False, "error": "Missing required parameters"}
        
        try:
            update_query = self._build_interaction_update_query(batch, updates)
            result = self.col.update_one(
                {
                    "period_id": period_id,
                    "location": location,
                    "report_type": report_type,
                    f"batches.{batch}.id": record_id
                },
                {"$set": update_query},
                array_filters=[{"elem.id": record_id}]
            )

            if result.matched_count == 0:
                logger.warning(f"No matching record for id: {record_id}")
                return {"success": False, "message": "No record matched"}

            return {"success": True, "modified_count": result.modified_count}

        except Exception as e:
            logger.exception("Failed to update interaction fields")
            return {"success": False, "error": str(e)}


class ExamNotificationHandler(BaseNotificationHandler):
    """Unified handler for all exam types - eliminates code duplication"""
    
    def __init__(self, collection=None):
        super().__init__(collection if collection is not None else whatsapp_stats_collection)
    
    def insert_or_update_details(self, info):
        date = info.pop("date", None)
        batch = info.pop("BatchNo", None)
        exam_type = info.pop("examType", None)
        
        # If examType not provided, try to infer from other fields or use default
        if not exam_type:
            exam_type = info.pop("exam_type", "Daily-Exam")
        
        logger.info(f"Processing exam notification - exam_type: {exam_type}, date: {date}, batch: {batch}")
        
        if not date or not batch:
            return {"success": False, "error": "Missing required fields: date or batch"}
        
        validation = self._validate_required_fields(info, ["id", "studentPhNumber", "sent"])
        if not validation["success"]:
            return validation
        
        details = {
            "studentId": info["id"],
            "studentPhNumber": info["studentPhNumber"],
            "sent": auto_format_datetime(info["sent"]),
            "last_sent": fmt_optional(0),
            "last_delivered": fmt_optional(0),
            "last_seen": fmt_optional(0),
            "last_interaction": fmt_optional(0),
            "recorded_at": auto_format_datetime(None),
        }

        # Use upsert for all exam types to prevent fragmentation
        return self._upsert_exam_record(date, exam_type, batch, details)
    
    def _upsert_exam_record(self, date, exam_type, batch, details):
        """Optimized upsert for Weekly/Monthly exams"""
        try:
            result = self.col.update_one(
                {"date": date, "exam_type": exam_type},
                {
                    "$push": {f"batches.{batch}": details},
                    "$set": {"last_updated": auto_format_datetime(None)},
                    "$setOnInsert": {
                        "date": date,
                        "exam_type": exam_type,
                        "created_at": auto_format_datetime(None)
                    }
                },
                upsert=True
            )
            return {"success": True, "modified_count": result.modified_count, "upserted_id": result.upserted_id}
        except Exception as e:
            logger.exception("Database update failed")
            return {"success": False, "error": str(e)}
    
    def _retry_exam_insert(self, date, exam_type, batch, details):
        """Use upsert for Daily exams to prevent fragmentation"""
        try:
            result = self.col.update_one(
                {"date": date, "exam_type": exam_type},
                {
                    "$push": {f"batches.{batch}": details},
                    "$set": {"last_updated": auto_format_datetime(None)},
                    "$setOnInsert": {
                        "date": date,
                        "exam_type": exam_type,
                        "created_at": auto_format_datetime(None)
                    }
                },
                upsert=True
            )
            return {"success": True, "modified_count": result.modified_count, "upserted_id": result.upserted_id}
        except Exception as e:
            logger.exception("Database update failed")
            return {"success": False, "error": str(e)}

    def update_interaction_fields(self, date, batch, studentPhNumber, updates, exam_type="Daily-Exam"):
        if not all([date, batch, studentPhNumber]):
            return {"success": False, "error": "Missing required parameters"}
        
        try:
            update_query = self._build_interaction_update_query(batch, updates)
            update_query[f"batches.{batch}.$[elem].recorded_at"] = auto_format_datetime(None)
            
            result = self.col.update_one(
                {
                    "date": date,
                    "exam_type": exam_type,
                    f"batches.{batch}.studentPhNumber": studentPhNumber
                },
                {"$set": update_query},
                array_filters=[{"elem.studentPhNumber": studentPhNumber}]
            )

            if result.matched_count == 0:
                logger.warning(f"No matching record for studentPhNumber: {studentPhNumber}")
                return {"success": False, "message": "No record matched"}

            return {"success": True, "modified_count": result.modified_count}

        except Exception as e:
            logger.exception("Failed to update interaction fields")
            return {"success": False, "error": str(e)}


class ExamNotificationFactory:
    """Factory using settings configuration"""
    
    @staticmethod
    def get_notification_handler(exam_type, collection=None):
        collection = collection if collection is not None else whatsapp_stats_collection
        if exam_type in ALLOWED_EXAM_TYPES:
            return ExamNotificationHandler(collection)
        else:
            logger.warning(f"Unknown exam type: {exam_type}, using default handler")
            return ExamNotificationHandler(collection)


class Daily_Exam_Notify(ExamNotificationHandler):
    """Daily exam notification handler - maintains backward compatibility"""
    
    def __init__(self, collection=None):
        super().__init__(collection if collection is not None else whatsapp_stats_collection)