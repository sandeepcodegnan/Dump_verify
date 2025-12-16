"""
Data Formatters and Transformers
Centralized formatting utilities following DRY principle
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId

def normalize_text(text: Optional[str]) -> str:
    """
    Normalize text output from compilers
    Centralized version replacing duplicate normalize() functions
    """
    if text is None:
        return ""
    
    normalized = (
        text.replace("↵", "\n")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .rstrip("\n")
    )
    
    return normalized

def serialize_document(obj: Any) -> Any:
    """Serialize MongoDB documents for JSON response"""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_document(item) for item in obj]
    if isinstance(obj, dict):
        return {key: serialize_document(value) for key, value in obj.items()}
    return obj

def format_question_response(question: Dict, question_type: str) -> Dict:
    """Format question document for API response"""
    formatted = serialize_document(question)
    if "_id" in formatted:
        formatted["questionId"] = formatted.pop("_id")
    formatted["questionType"] = question_type
    return formatted

def format_test_result(input_data: str, expected: str, actual: str, 
                      status: str, test_type: str) -> Dict:
    """Format test execution result"""
    return {
        "input": input_data,
        "expected_output": expected,
        "actual_output": actual,
        "status": status,
        "type": test_type
    }

def format_tags(tags: Any) -> List[str]:
    """Consistently format tags from various input formats"""
    if not tags:
        return []
    
    if isinstance(tags, str):
        return [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    elif isinstance(tags, list):
        result = []
        for tag in tags:
            if isinstance(tag, str):
                result.extend([t.strip().lower() for t in tag.split(",") if t.strip()])
            elif tag is not None:
                result.append(str(tag).strip().lower())
        return result
    else:
        return [str(tags).strip().lower()]

def clean_document(doc: Dict) -> Dict:
    """Remove empty values from document"""
    cleaned = {}
    for key, value in doc.items():
        if value not in (None, "", [], {}):
            if isinstance(value, dict):
                cleaned_nested = {k: v for k, v in value.items() if v}
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            else:
                cleaned[key] = value
    return cleaned