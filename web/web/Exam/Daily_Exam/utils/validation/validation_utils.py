"""Consolidated Validation Utilities - Single Source of Truth"""
from typing import Dict, Any
from datetime import datetime
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES

class ValidationUtils:
    """Unified validation utilities - eliminates all duplication"""
    
    @staticmethod
    def validate_required_fields(data: Dict, *fields: str) -> None:
        """Validate required fields exist and are not empty"""
        missing = [f for f in fields if not data.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
    
    @staticmethod
    def validate_positive_integer(value: Any, field_name: str) -> int:
        """Validate positive integer"""
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field_name} must be a positive integer")
        return value
    
    @staticmethod
    def validate_non_empty_string(value: Any, field_name: str) -> str:
        """Validate non-empty string"""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value.strip()
    
    @staticmethod
    def safe_int_conversion(value: Any, default: int = 0) -> int:
        """Safe integer conversion"""
        try:
            return int(value)
        except (ValueError, TypeError, OverflowError):
            return default
    
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Parse date string to datetime object"""
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime.strptime(date_str, "%Y-%m-%d")
    
    @staticmethod
    def validate_exam_type(exam_type: str) -> str:
        """Validate and normalize exam type"""
        if not exam_type:
            raise ValueError("Exam type is required")
        
        exam_type = exam_type.strip()
        if exam_type not in ALLOWED_EXAM_TYPES:
            raise ValueError(f"Invalid exam type '{exam_type}'. Allowed: {', '.join(sorted(ALLOWED_EXAM_TYPES))}")
        
        return exam_type