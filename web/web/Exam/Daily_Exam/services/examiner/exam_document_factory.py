"""Exam Document Factory - Individual Exam Document Creation (SoC)"""
import uuid
from typing import Dict, List
from web.Exam.Daily_Exam.utils.time.timeutils import seconds_to_time_str_12hr

class ExamDocumentFactory:
    """Handles exam document creation and formatting (SoC)"""
    
    @staticmethod
    def build_exam_documents(eligible_students: List[Dict], exam_config: Dict, window_config: Dict) -> List[Dict]:
        """Build exam documents for all eligible students"""
        new_exams = []
        
        for student in eligible_students:
            exam_data = ExamDocumentFactory._create_exam_document(student, exam_config, window_config)
            new_exams.append(exam_data)
        
        return new_exams
    
    @staticmethod
    def _create_exam_document(student: Dict, exam_config: Dict, window_config: Dict) -> Dict:
        """Create single exam document"""
        return {
            "examId": str(uuid.uuid4()),
            "studentId": student["id"],
            "startDate": exam_config["startDate"],
            "windowStartTime": window_config["windowStartTime"],
            "windowEndTime": window_config["windowEndTime"],
            "windowDurationSeconds": window_config["windowDurationSeconds"],
            "subjects": exam_config["subjects"],
            "totalExamTime": exam_config["totalExamTime"],
            "examName": exam_config["examName"],
            "batch": exam_config["batch"],
            "location": exam_config["location"]
        }
    
    @staticmethod
    def build_notification_data(exam_config: Dict, window_config: Dict, student_ids: List[str]) -> Dict:
        """Build notification data structure"""
        # Extract exam type from examName (e.g., "Daily-Exam-1" -> "Daily-Exam")
        exam_type = "-".join(exam_config["examName"].split("-")[:-1]) if "-" in exam_config["examName"] else "Daily-Exam"
        
        return {
            "examName": exam_config["examName"],
            "examType": exam_type,
            "subjects": exam_config["subjects"],
            "startDate": exam_config["startDate"],
            "windowStart": seconds_to_time_str_12hr(window_config["windowStartTime"]),
            "windowEnd": seconds_to_time_str_12hr(window_config["windowEndTime"]),
            "totalExamTime": exam_config["totalExamTime"],
            "batch": exam_config["batch"],
            "studentIds": student_ids
        }
    
    @staticmethod
    def build_result_response(created_count: int, exam_config: Dict, window_config: Dict) -> Dict:
        """Build final result response"""
        window_start_str = seconds_to_time_str_12hr(window_config["windowStartTime"])
        window_end_str = seconds_to_time_str_12hr(window_config["windowEndTime"])
        
        return {
            "message": f"{created_count} exams created with window period {window_start_str}-{window_end_str}",
            "examName": exam_config["examName"],
            "created": created_count,
            "windowInfo": {
                "windowStart": window_start_str,
                "windowEnd": window_end_str,
                "duration": window_config["windowDurationSeconds"]
            }
        }