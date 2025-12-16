"""Generate Exam Service - Create and schedule exams"""
from typing import Dict, Tuple
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils
from web.Exam.Daily_Exam.utils.security.security_utils import sanitize_string_input as sanitize_string
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.services.business_logic_validation.window_validation_service import WindowValidationService
from web.Exam.Daily_Exam.services.examiner.exam_document_factory import ExamDocumentFactory
from web.Exam.Daily_Exam.services.examiner.nested_exam_factory import NestedExamFactory
class GenerateExamService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def generate(self, data: Dict) -> Tuple[Dict, Dict]:
        ValidationUtils.validate_required_fields(data, "type", "batch", "subjects", "totalExamTime", "startDate", "managerLocation")
        
        exam_type = data["type"]
        total_exam_minutes = int(data["totalExamTime"])
        
        ExamValidationService.validate_exam_type(exam_type)
        ExamValidationService.validate_exam_duration(exam_type, total_exam_minutes)
        ExamValidationService.validate_weekday_restriction(exam_type, data["startDate"])
        
        window_config = self._get_window_config(exam_type)
        # Basic window validation
        if not window_config.get("windowDurationSeconds"):
            raise ValueError("Invalid window configuration")
        if total_exam_minutes * 60 > window_config["windowDurationSeconds"]:
            raise ValueError(f"Exam duration ({total_exam_minutes}min) exceeds window duration")
        
        # Validate exam scheduling time
        WindowValidationService.validate_exam_schedule_timing(data["startDate"], window_config)
        
        ExamValidationService.validate_exam_subjects(data["subjects"])
        
        exam_config = self._prepare_config(data, exam_type)
        eligible_students = self._get_students(exam_config)
        
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            optimized_exam = NestedExamFactory.build_optimized_exam_document(eligible_students, exam_config, window_config)
            
            if not self._create_optimized(exam_type, optimized_exam):
                raise ValueError("Failed to create optimized exam document")
            
            student_ids = [s["id"] for s in eligible_students]
            notification_data = NestedExamFactory.build_notification_data(exam_config, window_config, student_ids)
            result = NestedExamFactory.build_result_response(len(eligible_students), exam_config, window_config)
        else:
            new_exams = ExamDocumentFactory.build_exam_documents(eligible_students, exam_config, window_config)
            validated_exams = []
            for e in new_exams:
                try:
                    ExamValidationService.validate_exam_timing(e)
                    validated_exams.append(e)
                except ValueError:
                    continue
            
            if not validated_exams:
                raise ValueError("No eligible students found for exam generation")
            
            created_count = self._create_exams(exam_type, validated_exams)
            student_ids = [s["id"] for s in eligible_students]
            notification_data = ExamDocumentFactory.build_notification_data(exam_config, window_config, student_ids)
            result = ExamDocumentFactory.build_result_response(created_count, exam_config, window_config)
        
        return sanitize_mongo_document(result), notification_data
    
    def _get_window_config(self, exam_type: str) -> Dict:
        window_repo = self.repo_factory.get_window_config_repo()
        window_config = window_repo.find_by_exam_type(exam_type)
        if not window_config:
            raise ValueError(f"No window configuration found for {exam_type}. Please configure window periods first.")
        return window_config
    
    def _prepare_config(self, data: Dict, exam_type: str) -> Dict:
        batch = sanitize_string(data["batch"])
        start_date = sanitize_string(data["startDate"])
        manager_loc = sanitize_string(data["managerLocation"])
        
        exam_repo = self.repo_factory.get_exam_repo(exam_type)
        next_suffix = exam_repo.get_next_suffix(batch, exam_type)
        
        return {
            "startDate": start_date,
            "subjects": data["subjects"],
            "totalExamTime": int(data["totalExamTime"]),
            "examName": f"{exam_type}-{next_suffix}",
            "batch": batch,
            "location": manager_loc
        }
    
    def _get_students(self, exam_config: Dict) -> list:
        student_repo = self.repo_factory.get_student_repo()
        eligible_students = student_repo.find_eligible_students(
            exam_config["batch"], exam_config["location"], 
            exam_config["examName"].split("-")[0], exam_config["startDate"]
        )
        if not eligible_students:
            raise ValueError("No eligible students found")
        return eligible_students
    
    def _create_exams(self, exam_type: str, new_exams: list) -> int:
        exam_repo = self.repo_factory.get_exam_repo(exam_type)
        return exam_repo.create_bulk(new_exams)
    
    def _create_optimized(self, exam_type: str, optimized_exam: Dict) -> bool:
        optimized_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        return optimized_repo.create_optimized_exam(optimized_exam)
