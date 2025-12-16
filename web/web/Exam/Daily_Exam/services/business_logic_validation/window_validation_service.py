"""Window Domain Validation Service"""
from typing import Dict
from web.Exam.Daily_Exam.utils.time.timeutils import now_ist, seconds_to_time_str_12hr, parse_date_to_native, combine_date_time_native

class WindowValidationService:
    """Window timing domain-specific validations"""
    

    @staticmethod
    def validate_exam_schedule_timing(start_date: str, window_config: Dict) -> None:
        """Validate exam can be scheduled for given date and window"""
        now = now_ist()
        exam_date = parse_date_to_native(start_date)
        exam_end_time = combine_date_time_native(exam_date, window_config["windowEndTime"])
        
        if now > exam_end_time:
            raise ValueError(f"Cannot create exam for {start_date}. Window closed at {seconds_to_time_str_12hr(window_config['windowEndTime'])}")