"""
Dump API - Enterprise Architecture
Secure question dump operations with validation
"""
from flask import request
from web.jwt.auth_middleware import tester_required
from flask_restful import Resource
from web.Exam.Testing.services.dump_service import DumpService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class DumpAPI(Resource):
    """Refactored Dump API with security validation"""
    
    def __init__(self):
        self.dump_service = DumpService()
        self.error_handler = ErrorHandler()
    
    def options(self):
        """Handle CORS preflight"""
        return {}, 200
    @tester_required
    def post(self):
        """Process question dump with pagination"""
        try:
            data = request.get_json(silent=True) or {}
            
            # Pagination parameters - aligned with question API
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, int(request.args.get("limit", 10)))
            
            result = self.dump_service.process_dump(data, page, limit)
            
            return self.error_handler.create_success_response(result)
            
        except Exception as e:
            return self.error_handler.handle_error(e)
    
