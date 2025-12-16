"""Exam Retrieval Utilities - DRY utility for common exam operations"""
from typing import Dict
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.exceptions.exceptions import ExamNotFoundError, ValidationError
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils

class ExamRetrievalUtils:
    @staticmethod
    def get_exam_with_validation(exam_id: str, exam_type: str) -> Dict:
        """Get exam with validation - DRY utility for all services"""
        if not exam_id:
            raise ValidationError("examId is required")
        if not exam_type:
            raise ValidationError("examType is required")
        
        exam_type = ValidationUtils.validate_exam_type(exam_type)
        repo_factory = RepositoryFactory()
        
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = repo_factory.get_optimized_exam_repo(exam_type)
            exam = exam_repo.find_student_exam_by_id(exam_id)
        else:
            exam_repo = repo_factory.get_exam_repo(exam_type)
            exam = exam_repo.find_by_id(exam_id)
        
        if not exam:
            raise ExamNotFoundError("Exam record not found.")
        
        return exam