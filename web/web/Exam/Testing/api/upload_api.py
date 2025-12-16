"""
Upload API - Enterprise Architecture
Question upload with S3 integration and validation
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.upload_service import UploadService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class UploadAPI(Resource):
    """Refactored Upload API with S3 service integration"""
    
    def __init__(self):
        self.upload_service = UploadService()
        self.error_handler = ErrorHandler()
    
    @tester_required
    def post(self):
        """Upload questions with optional cover image"""
        try:
            # Handle file upload
            file_data = None
            if 'coverImage' in request.files:
                file = request.files['coverImage']
                if file and file.filename:
                    file_data = file.read()
            
            # Get questions data
            questions_data = request.form.get('data', '')
            
            # Process upload
            result = self.upload_service.upload_questions(file_data, questions_data)
            
            return self.error_handler.create_success_response(result)
            
        except Exception as e:
            return self.error_handler.handle_error(e)