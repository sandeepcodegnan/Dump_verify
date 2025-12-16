"""
Subjects API - Get tester's available subjects
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.subjects_service import SubjectsService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class SubjectsAPI(Resource):
    """API to get tester's subjects from Designation field"""
    
    def __init__(self):
        self.subjects_service = SubjectsService()
        self.error_handler = ErrorHandler()
    
    @tester_required
    def get(self):
        """Get tester's available subjects"""
        try:
            tester_id = request.args.get("id")
            subjects = self.subjects_service.get_tester_subjects(tester_id)
            return self.error_handler.create_success_response(subjects)
            
        except Exception as e:
            return self.error_handler.handle_error(e)