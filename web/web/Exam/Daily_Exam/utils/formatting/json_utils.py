"""JSON serialization utilities for MongoDB ObjectId handling"""
from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union

def serialize_objectid(obj: Any) -> Any:
    """Convert ObjectId and datetime objects to JSON serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_objectid(item) for item in obj]
    return obj

def sanitize_mongo_document(doc: Union[Dict, List, None]) -> Union[Dict, List, None]:
    """Sanitize MongoDB document for JSON serialization with additional validation"""
    if doc is None:
        return None
    return serialize_objectid(doc)