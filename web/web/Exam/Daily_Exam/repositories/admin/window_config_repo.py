"""Window Configuration Repository - Data Access Layer (SoC)"""
from web.Exam.exam_central_db import window_configs_collection
from web.Exam.Daily_Exam.utils.time.timeutils import now_ist

class WindowConfigRepo:
    def __init__(self):
        self.collection = window_configs_collection
    
    def upsert_config(self, exam_type: str, config: dict):
        """Create or update window configuration"""
        self.collection.update_one(
            {"examType": exam_type},
            {"$set": config},
            upsert=True
        )
    
    def find_active_configs(self) -> list:
        """Get all active window configurations"""
        return list(self.collection.find({"isActive": True}))
    
    def find_by_exam_type(self, exam_type: str) -> dict:
        """Get configuration by exam type"""
        return self.collection.find_one({"examType": exam_type, "isActive": True})
    
    def update_config(self, exam_type: str, update_data: dict) -> bool:
        """Update existing configuration"""
        result = self.collection.update_one(
            {"examType": exam_type, "isActive": True},
            {"$set": update_data}
        )
        return result.matched_count > 0  

    def delete_config(self, exam_type: str) -> bool:
        """Permanently delete configuration (hard delete)"""
        result = self.collection.delete_one({"examType": exam_type})
        return result.deleted_count > 0