"""Centralized error handling and responses - DRY principle"""
import logging
from typing import Tuple, Any
from flask import jsonify
from web.Exam.Daily_Exam.exceptions.exceptions import *

logger = logging.getLogger(__name__)



# ============= ERROR HANDLERS =============

def handle_service_error(e: Exception) -> Tuple[dict, int]:
    """Centralized error handling for services"""
    
    if isinstance(e, ValidationError):
        return {"success": False, "message": str(e)}, 400
    
    elif isinstance(e, ExamNotFoundError):
        return {"success": False, "message": str(e)}, 404
    
    elif isinstance(e, ExamAlreadyStartedError):
        return {"success": False, "message": str(e)}, 403
    
    elif isinstance(e, ExamAlreadySubmittedError):
        return {"success": False, "message": str(e)}, 403
    
    elif isinstance(e, ValueError):
        # Handle weekday restriction with 406 status code
        if "can only be conducted on Monday-Saturday" in str(e):
            return {"success": False, "message": str(e)}, 406
        # Handle time constraint violations with 406 status code
        if "duration cannot exceed" in str(e):
            return {"success": False, "message": str(e)}, 406
        # Handle other ValueError with the actual error message (like missing MCQ questions)
        return {"success": False, "message": str(e)}, 400
    
    else:
        sanitized_error = str(e).replace('\n', ' ').replace('\r', ' ')[:500]
        logger.error(f"Unexpected error: {sanitized_error}")
        return {"success": False, "message": "Server error"}, 500

