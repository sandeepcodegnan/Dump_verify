"""Available Exams Service - Get student's available exams"""
from typing import Dict, List
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.time.window_utils import WindowStatusChecker
from web.Exam.Daily_Exam.utils.student.student_eligibility_utils import check_eligibility_status
from web.Exam.Daily_Exam.utils.security.security_utils import validate_student_id

class AvailableExamsService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_available_exams(self, student_id: str, exam_type: str) -> Dict:
        student_id = validate_student_id(student_id)
        student_repo = self.repo_factory.get_student_repo()
        student = student_repo.find_by_id(student_id)
        
        if not student:
            raise ValueError("Student not found")
        
        # Check student eligibility
        eligibility_check = check_eligibility_status(student)
        if eligibility_check:
            return eligibility_check
        
        # Parse comma-separated exam types
        requested_types = [t.strip() for t in exam_type.split(',')]
        collections = [t for t in requested_types if t in ALLOWED_EXAM_TYPES]
        if not collections:  # Invalid exam types provided
            raise ValueError(f"Invalid exam type(s): {exam_type}")
        exams_data = {}
        total_exams = 0

        for collection in collections:
            if collection in {"Weekly-Exam", "Monthly-Exam"}:
                exam_repo = self.repo_factory.get_optimized_exam_repo(collection)
            else:
                exam_repo = self.repo_factory.get_exam_repo(collection)
            
            exams = exam_repo.get_student_exams(student_id)
            
            result_list = []
            for exam in exams:
                # Skip completed exams entirely
                if exam.get("attempt-status") is True:
                    continue
                
                if "windowStartTime" in exam and "windowEndTime" in exam:
                    window_status = WindowStatusChecker.check_window_status(exam, include_date_check=True)
                    # Filter out expired exams
                    if window_status["status"] == "expired":
                        continue
                else:
                    window_status = {"canStart": True, "status": "no_window", "message": "No window restriction"}
                
                result_list.append({
                    "_id": str(exam.get("_id", "")),
                    "examId": exam.get("examId"),
                    "examName": exam.get("examName"),
                    "totalExamTime": exam.get("totalExamTime"),
                    "startDate": exam.get("startDate"),
                    "windowStartTime": exam.get("windowStartTime"),
                    "windowEndTime": exam.get("windowEndTime"),
                    "attempt-status": exam.get("attempt-status"),
                    "subjects": self._extract_subjects(exam),
                    "windowStatus": window_status
                })
            
            exams_data[collection] = result_list
            total_exams += len(result_list)
                
        # Determine message based on results
        if total_exams == 0:
            message = "There are no exams currently scheduled for you. Please check back later."
            success = False
        else:
            message = "Exams Fetched Successfully"
            success = True
        
        return sanitize_mongo_document({
            "success": success,
            "message": message,
            "totalExams": total_exams,
            "exams": exams_data
        })   
 
    def _extract_subjects(self, exam: Dict) -> List[str]:
        if exam.get("paper"):
            return [item.get("subject") for item in exam.get("paper", []) if item.get("subject")]
        elif exam.get("subjects"):
            return [item.get("subject") or item.get("name") for item in exam.get("subjects", []) if item.get("subject") or item.get("name")]
        return []