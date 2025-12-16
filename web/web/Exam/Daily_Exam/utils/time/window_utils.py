"""Window Status Utilities - DRY Implementation"""
from typing import Dict
from datetime import datetime
from web.Exam.Daily_Exam.utils.time.timeutils import now_ist, time_to_seconds, seconds_to_time_str_12hr

class WindowStatusChecker:
    """Centralized window status checking logic (DRY principle)"""
    
    @staticmethod
    def check_window_status(exam: Dict, include_date_check: bool = True) -> Dict:
        """
        Universal window status checker
        
        Args:
            exam: Exam document with window fields
            include_date_check: Whether to check exam date (True for student, False for examiner)
        
        Returns:
            Dict with canStart, status, message, and optional extensionMinutes
        """
        # Check if exam has window configuration
        if "windowStartTime" not in exam or "windowEndTime" not in exam:
            return {"canStart": True, "status": "no_window", "message": "No window restriction"}
        
        now = now_ist()
        current_seconds = time_to_seconds(now.time())
        
        # Date validation (only for student-facing checks)
        if include_date_check:
            date_status = WindowStatusChecker._check_exam_date(exam, now)
            if date_status:
                return date_status
        
        # Time window validation
        return WindowStatusChecker._check_time_window(exam, current_seconds)
    
    @staticmethod
    def _check_exam_date(exam: Dict, now: datetime) -> Dict:
        """Check if exam date is valid (past/present/future)"""
        exam_date_str = exam.get("startDate")
        if not exam_date_str:
            return None
        
        try:
            exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
            current_date = now.date()
            
            if exam_date < current_date:
                return {
                    "canStart": False,
                    "status": "expired",
                    "message": f"Exam date ({exam_date_str}) has passed"
                }
            elif exam_date > current_date:
                return {
                    "canStart": False,
                    "status": "upcoming",
                    "message": f"Exam scheduled for {exam_date_str}. Please wait."
                }
        except ValueError:
            pass  # Invalid date format, continue with time-only check
        
        return None  # Same date, continue with time check
    
    @staticmethod
    def _check_time_window(exam: Dict, current_seconds: int) -> Dict:
        """Check time window status"""
        window_start = exam['windowStartTime']
        window_end = exam['windowEndTime']
        
        if current_seconds < window_start:
            return {
                "canStart": False,
                "status": "upcoming",
                "message": f"Exam window opens at {seconds_to_time_str_12hr(window_start)}. Please wait."
            }
        elif current_seconds <= window_end:
            # Active window - calculate extension if needed
            total_exam_seconds = exam['totalExamTime'] * 60
            end_time_seconds = current_seconds + total_exam_seconds
            extension_seconds = max(0, end_time_seconds - window_end)
            extension_minutes = extension_seconds // 60
            
            return {
                "canStart": True,
                "status": "active",
                "message": f"You can start now. Exam will finish at {seconds_to_time_str_12hr(end_time_seconds)}",
                "extensionMinutes": extension_minutes
            }
        else:
            return {
                "canStart": False,
                "status": "expired",
                "message": f"Exam window closed at {seconds_to_time_str_12hr(window_end)}"
            }