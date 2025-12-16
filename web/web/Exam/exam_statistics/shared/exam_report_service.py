"""Shared Exam Report Service - DRY & SOC Implementation"""
import datetime
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.exam_central_db import db

class ExamReportService:
    """Shared service for exam reporting - implements DRY and SOC principles"""
    
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def validate_and_parse_params(self, date_param, exam_type, location_param=None, batch_param=None):
        """Common validation and parsing logic (DRY)"""
        if exam_type not in ALLOWED_EXAM_TYPES:
            raise ValueError(f"Invalid exam type. Allowed: {', '.join(ALLOWED_EXAM_TYPES)}")
        
        try:
            report_dt = (
                datetime.datetime.strptime(date_param, "%Y-%m-%d")
                if date_param
                else datetime.datetime.utcnow() - datetime.timedelta(days=1)
            )
        except ValueError:
            raise ValueError("Invalid date, use YYYY-MM-DD.")
        
        return {
            "date_key": report_dt.strftime("%Y-%m-%d"),
            "exam_type": exam_type,
            "location_param": location_param,
            "batch_param": batch_param
        }
    
    def get_repository(self, exam_type):
        """Get appropriate repository based on exam type (SOC)"""
        return (self.repo_factory.get_optimized_exam_repo(exam_type) 
                if exam_type in {"Weekly-Exam", "Monthly-Exam"} 
                else self.repo_factory.get_exam_repo(exam_type))
    
    def build_query(self, date_key, location_param=None, batch_param=None):
        """Build common query object (DRY)"""
        query = {"startDate": date_key}
        if location_param and location_param.lower() != "all":
            query["location"] = location_param
        if batch_param:
            query["batch"] = batch_param
        return query
    
    def calculate_end_time(self, window_end_time, total_exam_time):
        """Calculate exam end time (DRY)"""
        if not window_end_time:
            return None
        total_seconds = window_end_time + (total_exam_time or 0) * 60
        hours, minutes = divmod(total_seconds // 60, 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def get_whatsapp_stats(self, date_key, batch_param):
        """Get WhatsApp statistics (DRY)"""
        ws_doc = db["whatsapp_stats"].find_one({"date": date_key}, {"batches." + batch_param: 1})
        wa_stats = ws_doc.get("batches", {}).get(batch_param, []) if ws_doc else []
        
        for stat in wa_stats:
            rec = stat.get("recorded_at")
            if isinstance(rec, datetime.datetime):
                stat["recorded_at"] = rec.isoformat()
        
        return wa_stats
    
    def merge_student_data(self, students, wa_stats):
        """Merge student data with WhatsApp stats (DRY)"""
        stats_map = {stat["studentId"]: stat for stat in wa_stats}
        return [{
            "id": stu["id"],
            "studentPhNumber": stu.get("studentPhNumber"),
            "name": stu.get("name"),
            "last_sent": stats_map.get(stu["id"], {}).get("last_sent"),
            "last_delivered": stats_map.get(stu["id"], {}).get("last_delivered"),
            "last_seen": stats_map.get(stu["id"], {}).get("last_seen"),
            "last_interaction": stats_map.get(stu["id"], {}).get("last_interaction"),
            "recorded_at": stats_map.get(stu["id"], {}).get("recorded_at"),
        } for stu in students]
    
    def get_time_conversion_pipeline(self):
        """Get MongoDB pipeline for time conversion (DRY)"""
        return {
            "window_start_time": {
                "$let": {
                    "vars": {
                        "hours": {"$floor": {"$divide": ["$windowStartTime", 3600]}},
                        "minutes": {"$floor": {"$divide": [{"$mod": ["$windowStartTime", 3600]}, 60]}}
                    },
                    "in": {
                        "$concat": [
                            {"$toString": {"$cond": [{"$lt": ["$$hours", 10]}, {"$concat": ["0", {"$toString": "$$hours"}]}, {"$toString": "$$hours"}]}},
                            ":",
                            {"$toString": {"$cond": [{"$lt": ["$$minutes", 10]}, {"$concat": ["0", {"$toString": "$$minutes"}]}, {"$toString": "$$minutes"}]}}
                        ]
                    }
                }
            },
            "window_end_time": {
                "$let": {
                    "vars": {
                        "hours": {"$floor": {"$divide": ["$windowEndTime", 3600]}},
                        "minutes": {"$floor": {"$divide": [{"$mod": ["$windowEndTime", 3600]}, 60]}}
                    },
                    "in": {
                        "$concat": [
                            {"$toString": {"$cond": [{"$lt": ["$$hours", 10]}, {"$concat": ["0", {"$toString": "$$hours"}]}, {"$toString": "$$hours"}]}},
                            ":",
                            {"$toString": {"$cond": [{"$lt": ["$$minutes", 10]}, {"$concat": ["0", {"$toString": "$$minutes"}]}, {"$toString": "$$minutes"}]}}
                        ]
                    }
                }
            }
        }
    
    def get_students_by_ids(self, student_ids, location_param=None):
        """Get student details by IDs (DRY)"""
        query = {"id": {"$in": student_ids}}
        if location_param:
            query["location"] = location_param
        return list(db["student_login_details"].find(
            query, {"_id": 0, "id": 1, "name": 1, "studentPhNumber": 1}
        ))
    
    def get_basic_counts(self, repo, query):
        """Get basic allocated/attempted counts (DRY)"""
        allocated = repo.collection.count_documents(query)
        attempted = repo.collection.count_documents({**query, "attempt-status": True})
        return allocated, attempted