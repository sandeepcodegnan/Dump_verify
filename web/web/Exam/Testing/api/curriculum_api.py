"""
Curriculum API - Enterprise Architecture
Clean separation of concerns with service layer
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.curriculum_service import CurriculumService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class CurriculumAPI(Resource):
    """Refactored Curriculum API with enterprise architecture"""
    
    def __init__(self):
        self.curriculum_service = CurriculumService()
        self.error_handler = ErrorHandler()
    @tester_required
    def get(self):
        """Get tester curriculum with subject-based pagination"""
        try:
            tester_id = request.args.get("id")
            subject_filter = request.args.get("subject")
            
            # Pagination parameters
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, int(request.args.get("limit", 10)))
            
            curriculum = self.curriculum_service.get_tester_curriculum(
                tester_id, subject_filter, page, limit
            )
            
            return self.error_handler.create_success_response(curriculum)
            
        except Exception as e:
            return self.error_handler.handle_error(e)