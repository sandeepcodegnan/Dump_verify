"""Exam List Service - Get mentor's exam list"""
from typing import Dict, List
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.utils.statistics.exam_statistics_utils import ExamStatisticsUtils

class ExamListService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_list(self, batch: str, subjects: List[str] = None, exam_type: str = "Daily-Exam") -> Dict:
        validated_exam_type = ExamValidationService.validate_exam_type(exam_type)
        
        if validated_exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(validated_exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(validated_exam_type)
        
        result = exam_repo.get_mentor_exam_list(batch, subjects)
        result["success"] = True
        
        # Convert to manager format
        if result.get("examNames"):
            # Sort in ascending order like manager
            try:
                sorted_names = sorted(result["examNames"], key=lambda n: int(n.split("-")[-1]))
            except (ValueError, IndexError):
                sorted_names = sorted(result["examNames"])
            
            exam_objects = [{"examName": name, "batch": batch} for name in sorted_names]
            result["exams"] = exam_objects
            # Add statistics
            try:
                ExamStatisticsUtils.add_statistics_to_exam_list(result, exam_repo, batch)
            except Exception as e:
                print(f"Statistics error: {e}")
                for exam in result["exams"]:
                    exam["statistics"] = {
                        "totalAllocated": 0,
                        "attemptedCount": 0,
                        "notAttemptedCount": 0,
                        "attemptedPercentage": 0.0
                    }
            # Remove examNames and batch from root
            result.pop("examNames", None)
            result.pop("batch", None)
        
        return sanitize_mongo_document(result)
