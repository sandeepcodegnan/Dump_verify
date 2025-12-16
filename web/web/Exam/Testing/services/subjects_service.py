"""
Subjects Service
Business logic for subjects operations
"""
from typing import Dict
from .base_service import BaseService
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError
from web.Exam.exam_central_db import testers_collection

class SubjectsService(BaseService):
    """Service for subjects operations"""
    
    def get_tester_subjects(self, tester_id: str) -> Dict:
        """Get subjects from tester's Designation field"""
        if not tester_id:
            raise ValidationError("'id' query parameter is required")
        
        doc = testers_collection.find_one(
            {"id": tester_id},
            {"_id": 0, "Designation": 1}
        )
        
        if not doc:
            raise ValidationError("Tester not found")
        
        subjects = doc.get("Designation", [])
        
        return {
            "id": tester_id,
            "subjects": [subject.lower() for subject in subjects]
        }