"""Exam Toggle Repository - Data Access Layer"""
from web.Exam.exam_central_db import exam_toggle_collection
from web.Exam.Daily_Exam.utils.time.timeutils import now_ist

class ExamToggleRepo:
    def __init__(self):
        self.collection = exam_toggle_collection
    
    def upsert_toggle(self, exam_type: str, is_enabled: bool):
        """Create or update toggle state"""
        self.collection.update_one(
            {"examType": exam_type},
            {"$set": {"examType": exam_type, "isEnabled": is_enabled, "updatedAt": now_ist()}},
            upsert=True
        )
    
    def get_all_toggles(self) -> list:
        """Get all exam toggle states"""
        return list(self.collection.find({}, {"_id": 0, "examType": 1, "isEnabled": 1}))
