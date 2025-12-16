"""
Submission API - Refactored with Enterprise Architecture
Following SoC and DRY principles
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.submission_service import SubmissionService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class SubmissionAPI(Resource):
    """Refactored Test Submission API"""
    
    def __init__(self):
        self.submission_service = SubmissionService()
        self.error_handler = ErrorHandler()
    
    @tester_required
    def post(self):
        """Process code/SQL submission"""
        try:
            data = request.get_json(force=True)
            result = self.submission_service.process_submission(data)
            return self.error_handler.create_success_response(result)
            
        except Exception as e:
            return self.error_handler.handle_error(e)