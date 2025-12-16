"""Exam Domain Validation Service"""
from datetime import datetime
from typing import Dict, List, Any
from web.Exam.Daily_Exam.config.settings import (
    EXAM_TIME_CONSTRAINTS, WEEKDAY_ONLY_EXAMS
)
from web.Exam.Daily_Exam.utils.time.week_utils import validate_weekday_only
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils

class ExamValidationService:
    """Centralized validation service for all exam-related validations"""
    
    # Core Exam Validations
    @staticmethod
    def validate_exam_type(exam_type: str) -> str:
        """Validate and normalize exam type"""
        return ValidationUtils.validate_exam_type(exam_type)
    
    @staticmethod
    def validate_exam_duration(exam_type: str, total_exam_minutes: int) -> None:
        """Validate exam duration constraints"""
        ValidationUtils.validate_positive_integer(total_exam_minutes, "Exam duration")
        ExamValidationService._validate_time_constraint(exam_type, total_exam_minutes)
    
    @staticmethod
    def validate_weekday_restriction(exam_type: str, start_date: str) -> None:
        """Validate weekday restrictions"""
        ExamValidationService._validate_weekday_restriction(exam_type, start_date)
    

    
    @staticmethod
    def validate_exam_timing(exam_data: Dict) -> bool:
        """Validate exam timing configuration"""
        total_time = exam_data.get("totalExamTime", 0)
        subjects = exam_data.get("subjects", [])
        
        if not subjects:
            return False
            
        subject_time_sum = sum(s.get("totalTime", 0) for s in subjects)
        return subject_time_sum <= total_time
    
    @staticmethod
    def validate_exam_subjects(subjects: List[Dict]) -> None:
        """Validate exam subjects configuration"""
        if not subjects:
            raise ValueError("At least one subject is required")
            
        for subject in subjects:
            if not subject.get("subject"):
                raise ValueError("Subject name is required")
            if not subject.get("totalTime"):
                raise ValueError(f"Total time is required for subject {subject.get('subject')}")
    

    # Exam Scheduling Validations
    @staticmethod
    def validate_exam_schedule(exam_data: Dict[str, Any]) -> None:
        """Validate exam scheduling constraints"""
        ValidationUtils.validate_required_fields(exam_data, "exam_type", "duration", "scheduled_date")
        
        exam_type = exam_data["exam_type"]
        duration = exam_data["duration"]
        scheduled_date = exam_data["scheduled_date"]
        
        # Validate time constraints
        ExamValidationService._validate_time_constraint(exam_type, duration)
        
        # Validate weekday restrictions
        ExamValidationService._validate_weekday_restriction(exam_type, scheduled_date)
    
    @staticmethod
    def _validate_time_constraint(exam_type: str, duration: int) -> None:
        """Validate exam duration against configured constraints"""
        max_duration = EXAM_TIME_CONSTRAINTS.get(exam_type)
        if max_duration and duration > max_duration:
            raise ValueError(f"{exam_type} duration cannot exceed {max_duration} minutes")
    
    @staticmethod
    def _validate_weekday_restriction(exam_type: str, scheduled_date: str) -> None:
        """Validate weekday restrictions for specific exam types"""
        if exam_type in WEEKDAY_ONLY_EXAMS:
            validate_weekday_only(scheduled_date, exam_type)