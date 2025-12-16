"""Exam Dates Service - Get actual conducted exam dates"""
from typing import Dict, List
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils

class ExamDatesService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_conducted_exam_dates(self, batch_no: str, exam_type: str) -> Dict:
        """Get actual conducted exam dates for a batch and exam type"""
        ValidationUtils.validate_exam_type(exam_type)
        
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
            pipeline = [
                {"$match": {"batch": {"$regex": f"^{batch_no}$", "$options": "i"}, "students": {"$exists": True, "$ne": []}}},
                {"$unwind": "$students"},
                {"$match": {"students.attempt-status": True}},
                {"$group": {"_id": "$startDate"}},
                {"$sort": {"_id": -1}}
            ]
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
            pipeline = [
                {"$match": {"batch": {"$regex": f"^{batch_no}$", "$options": "i"}, "attempt-status": True}},
                {"$group": {"_id": "$startDate"}},
                {"$sort": {"_id": -1}}
            ]
        
        conducted_dates = list(exam_repo.collection.aggregate(pipeline))
        dates = [doc["_id"] for doc in conducted_dates if doc["_id"]]
        
        return {
            "success": True,
            "batch": batch_no,
            "examType": exam_type,
            "conductedDates": dates
        }