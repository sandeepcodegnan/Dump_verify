"""Student Repository - Data Access Layer (SoC)"""
from typing import Dict, List, Optional
from web.Exam.exam_central_db import student_collection, get_db
from web.Exam.Daily_Exam.repositories.exam.exam_pipelines import build_eligible_students_pipeline

class StudentRepo:
    def __init__(self):
        self.collection = student_collection
        self.db = get_db()
    
    def find_by_id(self, student_id: str) -> Optional[Dict]:
        return self.collection.find_one({"id": student_id})
    
    def find_eligible_students(self, batch: str, location: str, exam_type: str, date: str) -> List[Dict]:
        pipeline = build_eligible_students_pipeline(batch, location, exam_type, date)
        return list(self.collection.aggregate(pipeline))
    
