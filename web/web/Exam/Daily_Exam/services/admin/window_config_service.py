"""Window Configuration Service - Business Logic Layer (SoC)"""
from datetime import time, datetime
from zoneinfo import ZoneInfo
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.time.timeutils import (
    time_to_seconds, seconds_to_time_str_12hr, calculate_duration
)

class WindowConfigService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def create_window_config(self, data: dict) -> dict:
        ValidationUtils.validate_required_fields(data, "examType", "windowStartTime", "windowEndTime")
        
        exam_type = data["examType"]
        start_time_str = data["windowStartTime"]
        end_time_str = data["windowEndTime"]
        
        # Use DRY utility functions
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)
        duration_seconds = calculate_duration(start_seconds, end_seconds)
        
        config = {
            "examType": exam_type,
            "windowStartTime": start_seconds,  # Native int (seconds since midnight)
            "windowEndTime": end_seconds,      # Native int (seconds since midnight)
            "windowDurationSeconds": duration_seconds,
            "isActive": True,
            "createdAt": datetime.now(ZoneInfo("Asia/Kolkata")),
            "updatedAt": datetime.now(ZoneInfo("Asia/Kolkata"))
        }
        
        window_repo = self.repo_factory.get_window_config_repo()
        window_repo.upsert_config(exam_type, config)
        
        return sanitize_mongo_document({
            "message": "Window configuration saved",
            "examType": exam_type,
            "windowStartTime": data["windowStartTime"],
            "windowEndTime": data["windowEndTime"],
            "windowDurationSeconds": duration_seconds
        })
    
    def get_all_configs(self) -> dict:
        window_repo = self.repo_factory.get_window_config_repo()
        configs = window_repo.find_active_configs()
        
        result = []
        for config in configs:
            result.append({
                "examType": config["examType"],
                "windowStartTime": seconds_to_time_str_12hr(config["windowStartTime"]),
                "windowEndTime": seconds_to_time_str_12hr(config["windowEndTime"]),
                "windowDurationSeconds": config["windowDurationSeconds"]
            })
        
        return sanitize_mongo_document({"configs": result})
    
    def get_config_by_type(self, exam_type: str) -> dict:
        window_repo = self.repo_factory.get_window_config_repo()
        config = window_repo.find_by_exam_type(exam_type)
        
        if not config:
            raise ValueError("Configuration not found")
        
        # Convert seconds back to time format
        start_seconds = config["windowStartTime"]
        end_seconds = config["windowEndTime"]
        
        return sanitize_mongo_document({
            "examType": config["examType"],
            "windowStartTime": seconds_to_time_str_12hr(start_seconds),
            "windowEndTime": seconds_to_time_str_12hr(end_seconds),
            "windowDurationSeconds": config["windowDurationSeconds"]
        })
    
    def update_config(self, exam_type: str, data: dict) -> dict:
        ValidationUtils.validate_required_fields(data, "windowStartTime", "windowEndTime")
        
        start_time_str = data["windowStartTime"]
        end_time_str = data["windowEndTime"]
        
        # Use DRY utility functions
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)
        duration_seconds = calculate_duration(start_seconds, end_seconds)
        
        update_data = {
            "windowStartTime": start_seconds,  # Native int (seconds since midnight)
            "windowEndTime": end_seconds,      # Native int (seconds since midnight)
            "windowDurationSeconds": duration_seconds,
            "updatedAt": datetime.now(ZoneInfo("Asia/Kolkata"))
        }
        
        window_repo = self.repo_factory.get_window_config_repo()
        success = window_repo.update_config(exam_type, update_data)
        
        if not success:
            raise ValueError("Configuration not found")
        
        return sanitize_mongo_document({
            "message": "Configuration updated",
            "examType": exam_type,
            "windowStartTime": data["windowStartTime"],
            "windowEndTime": data["windowEndTime"],
            "windowDurationSeconds": duration_seconds
        })
    

    def delete_config(self, exam_type: str) -> dict:
        """Hard delete - permanently remove configuration"""
        window_repo = self.repo_factory.get_window_config_repo()
        success = window_repo.delete_config(exam_type)
        
        if not success:
            raise ValueError("Configuration not found")
        
        return sanitize_mongo_document({
            "message": "Configuration permanently deleted",
            "examType": exam_type
        })