"""Security utilities - DRY principle"""
import re
from typing import Any, Union
from bson import ObjectId
from bson.errors import InvalidId

def sanitize_string_input(value: Any) -> str:
    """Sanitize string input to prevent injection"""
    if not isinstance(value, str):
        raise ValueError("Input must be string")
    return str(value).strip()

def validate_object_id(obj_id: Any) -> str:
    """Validate and return ObjectId as string"""
    if isinstance(obj_id, dict):
        raise ValueError("ObjectId cannot be dict (NoSQL injection attempt)")
    try:
        return str(ObjectId(obj_id))
    except (InvalidId, TypeError):
        raise ValueError("Invalid ObjectId format")

def validate_collection_name(name: str) -> str:
    """Validate collection name against whitelist"""
    from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
    if name not in ALLOWED_EXAM_TYPES:
        raise ValueError(f"Invalid collection: {name}")
    return name

def sanitize_regex_input(pattern: str) -> str:
    """Escape regex metacharacters"""
    return re.escape(str(pattern).strip())

def validate_student_id(student_id: Any) -> str:
    """Validate student ID format"""
    if isinstance(student_id, dict):
        raise ValueError("Student ID cannot be dict")
    return sanitize_string_input(student_id)

# validate_exam_type moved to validators.py to avoid duplication