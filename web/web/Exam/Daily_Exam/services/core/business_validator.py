"""Business Logic Validator - SoC Implementation"""
from typing import Dict, List
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES

class BusinessValidator:
    """Centralized business logic validation (SoC - belongs in services layer)"""
    
    @staticmethod
    def validate_exam_type(exam_type: str) -> str:
        """Strictly validate exam type against business rules"""
        if not exam_type:
            raise ValueError("Exam type is required")
        
        exam_type = exam_type.strip()
        if exam_type not in ALLOWED_EXAM_TYPES:
            raise ValueError(f"Invalid exam type '{exam_type}'. Allowed types: {', '.join(sorted(ALLOWED_EXAM_TYPES))}")
        
        return exam_type    

    @staticmethod
    def validate_exam_timing(exam: Dict) -> bool:
        """Validate exam timing business rules (Window-based system)"""
        # Business rule: Must have valid exam duration
        if not exam.get("totalExamTime") or exam.get("totalExamTime") <= 0:
            return False
        
        # Business rule: Must have startDate (exam date)
        if not exam.get("startDate"):
            return False
        
        return True
    
    @staticmethod
    def validate_exam_subjects(subjects: List[Dict]) -> bool:
        """Validate exam subjects business rules"""
        if not subjects or len(subjects) == 0:
            return False
        
        for subject in subjects:
            if not subject.get("subject"):
                return False
            
            # Business rule: Must have at least one question type
            mcqs = subject.get("selectedMCQs", {})
            subject_name = subject.get("subject", "").lower()
            
            # Check if SQL subject
            from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
            is_sql_subject = subject_name in SQL_SUBJECTS
            
            if is_sql_subject:
                queries = subject.get("selectedQuery", {})
                if not mcqs and not queries:
                    return False
            else:
                coding = subject.get("selectedCoding", {})
                if not mcqs and not coding:
                    return False
        
        return True