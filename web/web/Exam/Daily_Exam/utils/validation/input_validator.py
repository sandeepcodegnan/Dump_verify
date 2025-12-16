"""Centralized Input Validation - DRY Implementation"""
from typing import Dict, Any, List
from web.Exam.Daily_Exam.utils.security.security_utils import sanitize_string_input, validate_object_id
from .validation_utils import ValidationUtils

class InputValidator:
    """Centralized input validation to eliminate duplication"""
    
    @staticmethod
    def validate_exam_request(data: Dict) -> Dict:
        """Validate exam-related request data"""
        from web.Exam.Daily_Exam.services.business_logic_validation import ExamValidationService
        
        ValidationUtils.validate_required_fields(data, "examId", "collectionName")
        
        return {
            "examId": sanitize_string_input(data["examId"]),
            "collectionName": ExamValidationService.validate_exam_type(data["collectionName"])
        }
    
    @staticmethod
    def validate_batch_date_params(params: Dict) -> Dict:
        """Validate batch and date parameters"""
        ValidationUtils.validate_required_fields(params, "batch", "date")
        
        return {
            "batch": sanitize_string_input(params["batch"]),
            "date": sanitize_string_input(params["date"])
        }
    
    @staticmethod
    def validate_student_id(student_id: str) -> str:
        """Validate student ID format"""
        if not student_id:
            raise ValueError("Student ID is required")
        return sanitize_string_input(student_id)

def get_json_data():
    """Centralized JSON parsing"""
    from flask import request
    return request.get_json() or {}

def get_query_params(*required_params):
    """Centralized query parameter extraction with validation"""
    from flask import request
    params = {}
    missing = []
    
    for param in required_params:
        value = request.args.get(param, "").strip()
        if not value:
            missing.append(param)
        params[param] = value
    
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")
    
    return params

def parse_subjects_filter():
    """Parse subjects filter from query parameters"""
    from flask import request
    raw_list = request.args.getlist("subjects")
    subjects = []
    
    for raw in raw_list:
        processed_subject = raw.strip()
        if processed_subject.startswith("[") and processed_subject.endswith("]"):
            processed_subject = processed_subject[1:-1]
        for part in processed_subject.split(","):
            val = part.strip().strip('"\'')
            if val:
                subjects.append(val)
    
    return subjects

def get_optional_query_params(**param_defaults):
    """Get optional query parameters with defaults"""
    from flask import request
    params = {}
    
    for param, default in param_defaults.items():
        params[param] = request.args.get(param, default)
    
    return params

def get_single_query_param(param_name, required=True):
    """Get single query parameter with validation"""
    from flask import request
    value = request.args.get(param_name)
    
    if required and not value:
        raise ValueError(f"Missing required parameter: {param_name}")
    
    return value

def get_default_date():
    """Get yesterday's date as default"""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")