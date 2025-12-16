"""Exam Toggle Service - Business Logic Layer"""
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.config.settings import DEFAULT_EXAM_TOGGLE_STATE, ALLOWED_EXAM_TYPES

class ExamToggleService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def toggle_exam(self, exam_type: str, is_enabled: bool) -> dict:
        """Toggle exam on/off"""
        exam_toggle_repo = self.repo_factory.get_exam_toggle_repo()
        exam_toggle_repo.upsert_toggle(exam_type, is_enabled)
        
        return sanitize_mongo_document({
            "message": f"Exam {exam_type} {'enabled' if is_enabled else 'disabled'}",
            "examType": exam_type,
            "isEnabled": is_enabled
        })
    
    def get_all_toggles(self) -> dict:
        """Get all exam toggle states with defaults in alphabetical order"""
        exam_toggle_repo = self.repo_factory.get_exam_toggle_repo()
        db_toggles = exam_toggle_repo.get_all_toggles()
        
        # Create dict from DB data for quick lookup
        db_toggle_dict = {toggle["examType"]: toggle["isEnabled"] for toggle in db_toggles}
        
        # Build result with sorted exam types, defaulting to disabled
        result_toggles = [{
            "examType": exam_type,
            "isEnabled": db_toggle_dict.get(exam_type, DEFAULT_EXAM_TOGGLE_STATE)
        } for exam_type in sorted(ALLOWED_EXAM_TYPES)]
        
        return sanitize_mongo_document({"toggles": result_toggles})