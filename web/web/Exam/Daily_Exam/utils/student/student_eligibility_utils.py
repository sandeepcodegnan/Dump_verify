"""Student Eligibility Utilities - Check student eligibility for exams"""
from typing import Dict


def is_dropout(student: Dict) -> bool:
    """Check if student is a dropout."""
    batch_no = student.get("BatchNo", "")
    return batch_no.startswith("DROPOUTS-")


def is_placed(student: Dict) -> bool:
    """Check if student is placed."""
    return student.get("placed") == True


def check_eligibility_status(student: Dict) -> Dict | None:
    """
    Check student eligibility status (dropout or placed).
    Returns response dict if ineligible, None if eligible.
    """
    if is_dropout(student):
        return {"message": "You are DROPOUT Student!", "status": "DROPOUT"}
    
    if is_placed(student):
        return {
            "status": "placed",
            "message": "No exams ahead you are already placed and ready to conquer your career!"
        }
    
    return None
