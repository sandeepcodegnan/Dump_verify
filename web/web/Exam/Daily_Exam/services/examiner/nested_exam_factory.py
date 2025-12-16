"""Nested Exam Factory - Optimized Document with Nested Students"""
import uuid
from typing import Dict, List
from web.Exam.Daily_Exam.utils.time.timeutils import seconds_to_time_str_12hr

class NestedExamFactory:
    """Creates single exam document with nested student arrays for Weekly/Monthly exams"""
    
    @staticmethod
    def build_optimized_exam_document(eligible_students: List[Dict], exam_config: Dict, window_config: Dict) -> Dict:
        """Build single optimized exam document with nested student data"""
        
        # Generate document ID
        doc_id = f"{exam_config['examName'].lower()}-{exam_config['batch'].lower()}-{exam_config['location'].lower()}-{exam_config['startDate']}"
        
        # Build students array with individual exam IDs
        students = [{
            "examId": str(uuid.uuid4()),
            "studentId": student["id"],
            "start-status": False,
            "attempt-status": False,
            "startTimestamp": None,
            "submitTimestamp": None,
            "paper": None,
            "analysis": None
        } for student in eligible_students]
        
        # Build optimized document structure
        return {
            "_id": doc_id,
            "examName": exam_config["examName"],
            "batch": exam_config["batch"],
            "location": exam_config["location"],
            "startDate": exam_config["startDate"],
            "windowStartTime": window_config["windowStartTime"],
            "windowEndTime": window_config["windowEndTime"],
            "windowDurationSeconds": window_config["windowDurationSeconds"],
            "totalExamTime": exam_config["totalExamTime"],
            "subjects": exam_config["subjects"],
            "students": students
        }
    
    @staticmethod
    def build_notification_data(exam_config: Dict, window_config: Dict, student_ids: List[str]) -> Dict:
        """Build notification data structure"""
        # Extract exam type from examName (e.g., "Weekly-Exam-1" -> "Weekly-Exam")
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
    def build_result_response(student_count: int, exam_config: Dict, window_config: Dict) -> Dict:
        """Build final result response"""
        window_start_str = seconds_to_time_str_12hr(window_config["windowStartTime"])
        window_end_str = seconds_to_time_str_12hr(window_config["windowEndTime"])
        
        return {
            "message": f"1 optimized exam document created for {student_count} students with window period {window_start_str}-{window_end_str}",
            "examName": exam_config["examName"],
            "created": 1,
            "studentsCount": student_count,
            "windowInfo": {
                "windowStart": window_start_str,
                "windowEnd": window_end_str,
                "duration": window_config["windowDurationSeconds"]
            }
        }