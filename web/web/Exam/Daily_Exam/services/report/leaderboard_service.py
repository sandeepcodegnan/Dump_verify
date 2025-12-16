"""Leaderboard Service - Business Logic Layer (SoC)"""
from typing import Dict, List
from datetime import datetime
from hashlib import sha256
from gridfs import GridFS
from web.Exam.exam_central_db import db
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.pagination.pagination_utils import build_paginated_response
from web.Exam.Daily_Exam.utils.cache.cache_utils import leaderboard_cache
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils
from web.Exam.Daily_Exam.services.common.image_service import ImageService, GridFSImageProvider
from web.Exam.Daily_Exam.services.report.leaderboard_formatter import LeaderboardFormatter

class LeaderboardService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
        self.cache = leaderboard_cache
        
        # Dependency injection (DIP)
        fs = GridFS(db)
        image_provider = GridFSImageProvider(fs)
        image_service = ImageService(image_provider)
        self.formatter = LeaderboardFormatter(image_service)

    
    def get_batch_leaderboard(self, exam_type: str, batch: str, date: str = None, location: str = None, page: int = 1, limit: int = 10, student_id: str = None) -> Dict:
        """Get leaderboard for batch on specific date with original complex logic"""
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Check cache first
        cache_key = self._generate_cache_key(exam_type, batch, date, location, page, limit, student_id)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        exam_type = ValidationUtils.validate_exam_type(exam_type)
        
        if not location:
            raise ValueError("Missing required parameter: location")
        
        # Use optimized repo for Weekly/Monthly exams
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
        
        # Try to get data for requested date first
        results = exam_repo.get_leaderboard(date, batch, location)
        requested_date = date
        message = None
        
        # If no results, try recent exam
        if not results:
            recent_exam = exam_repo.get_recent_exam_date(batch, location)
            if recent_exam:
                recent_date = recent_exam.get("startDate")
                recent_exam_name = recent_exam.get("examName", "")
                
                if recent_date:
                    results = exam_repo.get_leaderboard(recent_date, batch, location)
                    if results:
                        message = f"No exam data found for {requested_date}. Showing data from {recent_date} ({recent_exam_name})."
                        requested_date = recent_date
        
        if not results:
            raise ValueError(f"No exam data found for batch {batch} and location {location}. Please check if exams have been conducted for this batch.")
        
        # Build leaderboard using formatter service
        leaderboard = self.formatter.format_leaderboard(results)
        
        # If no students in leaderboard, raise error
        if not leaderboard:
            raise ValueError(f"No students found in leaderboard for batch {batch} and location {location} on {requested_date}.")
            
        exam_name = results[0].get("examName", "") if results else ""
        
        # Apply pagination
        additional_fields = {
            "batch": batch,
            "location": location,
            "date": requested_date,
            "examName": exam_name
        }
        
        if message:
            additional_fields["message"] = message
        
        response_data = build_paginated_response(
            success=True,
            data=leaderboard,
            page=page,
            limit=limit,
            additional_fields=additional_fields
        )
        
        # Add student position tracking using full leaderboard
        if student_id:
            response_data = self._add_student_position(response_data, student_id, leaderboard, page, limit)
        
        final_result = sanitize_mongo_document(response_data)
        final_result["cached"] = False
        
        # Cache the result
        self.cache.put(cache_key, final_result)
        
        return final_result
    

    
    def _add_student_position(self, response_data: Dict, student_id: str, full_leaderboard: List[Dict], current_page: int, limit: int) -> Dict:
        """Add student position tracking with correct rank calculation"""
        # Find student in FULL leaderboard (before pagination)
        student_rank = None
        student_data = None
        
        for student in full_leaderboard:
            if student.get("studentId") == student_id:
                student_rank = student.get("rank")  # Use pre-calculated rank
                student_data = student.copy()
                break
        
        if student_rank:
            student_page = ((student_rank - 1) // limit) + 1
            is_on_current_page = student_page == current_page
            
            response_data["student_data"] = {
                "student_id": student_id,
                "rank": student_rank,
                "page": student_page,
                "is_on_current_page": is_on_current_page,
                **student_data
            }
            
            # Mark current user in leaderboard if on current page
            if is_on_current_page:
                for item in response_data["data"]:
                    if item.get("studentId") == student_id:
                        item["is_current_user"] = True
                        break
        
        return response_data
    
    def _generate_cache_key(self, exam_type: str, batch: str, date: str, location: str, page: int, limit: int, student_id: str) -> str:
        """Generate cache key for leaderboard"""
        key_data = f"{exam_type}:{batch}:{date}:{location}:{page}:{limit}:{student_id or ''}"
        return sha256(key_data.encode()).hexdigest()