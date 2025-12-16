"""Exam Statistics Utils - Common statistics calculation for exams"""
from typing import Dict, Optional

class ExamStatisticsUtils:
    @staticmethod
    def add_exam_statistics(exam: Dict, exam_repo, batch: str, location: Optional[str] = None):
        """Add attempted statistics to exam data"""
        exam_name = exam.get("examName")
        if not exam_name:
            return
        
        # Build match filter
        match_filter = {"batch": batch, "examName": exam_name}
        if location:
            match_filter["location"] = location
        
        # Get exam reports data for this specific exam
        exams_data = exam_repo.get_batch_reports_data(match_filter)
        
        if not exams_data:
            exam["statistics"] = {
                "totalAllocated": 0,
                "attemptedCount": 0,
                "notAttemptedCount": 0,
                "attemptedPercentage": 0.0
            }
            return
        
        # Count unique students and their attempt status
        student_attempts = {}
        for exam_data in exams_data:
            student = exam_data.get("student")
            if student and student.get("id"):
                student_id = student["id"]
                attempted = exam_data.get("attempt-status", False)
                student_attempts[student_id] = attempted
        
        total_allocated = len(student_attempts)
        attempted_count = sum(1 for attempted in student_attempts.values() if attempted)
        not_attempted_count = total_allocated - attempted_count
        attempted_percentage = (attempted_count / total_allocated * 100) if total_allocated > 0 else 0.0
        
        exam["statistics"] = {
            "totalAllocated": total_allocated,
            "attemptedCount": attempted_count,
            "notAttemptedCount": not_attempted_count,
            "attemptedPercentage": round(attempted_percentage, 2)
        }
    
    @staticmethod
    def add_statistics_to_exam_list(result: Dict, exam_repo, batch: str, location: Optional[str] = None):
        """Add statistics to all exams in a result list"""
        if result.get("success"):
            exams_list = result.get("data") or result.get("exams")
            if exams_list:
                for exam in exams_list:
                    ExamStatisticsUtils.add_exam_statistics(exam, exam_repo, batch, location)