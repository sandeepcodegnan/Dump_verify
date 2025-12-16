"""Exam Day List Service - Get examiner's exam schedule"""
from typing import Dict
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.utils.statistics.exam_statistics_utils import ExamStatisticsUtils

class ExamDayListService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_list(self, batch: str, location: str, exam_type: str = "Daily-Exam") -> Dict:
        validated_exam_type = ExamValidationService.validate_exam_type(exam_type)
        
        if validated_exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(validated_exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(validated_exam_type)
        
        result = exam_repo.get_exam_day_list(batch, location)
        
        # Add statistics for each exam
        ExamStatisticsUtils.add_statistics_to_exam_list(result, exam_repo, batch, location)
        
        return sanitize_mongo_document(result)
