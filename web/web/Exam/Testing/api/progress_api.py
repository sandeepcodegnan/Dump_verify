"""
Progress API - Enterprise Architecture
Optimized progress reporting with service layer
"""
from flask_restful import Resource
from flask import request
from web.jwt.auth_middleware import admin_required
from web.Exam.Testing.services.progress_service import ProgressService

class TesterOverallAPI(Resource):
    """API 1: Overall testers with aggregated stats"""
    
    def __init__(self):
        self.progress_service = ProgressService()
    
    @admin_required
    def get(self):
        """Get all testers with overall stats"""
        date = request.args.get('date')
        if not date:
            return {"success": False, "message": "Date parameter is required"}, 400
        
        try:
            result = self.progress_service.get_testers_overall(date)
            return result, 200
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

class TesterByIdAPI(Resource):
    """API 2: Tester by internId with subjects and stats"""
    
    def __init__(self):
        self.progress_service = ProgressService()
    
    @admin_required
    def get(self, intern_id):
        """Get tester by internId with subjects and stats"""
        date = request.args.get('date')
        if not date:
            return {"success": False, "message": "Date parameter is required"}, 400
        
        try:
            result = self.progress_service.get_tester_by_id(intern_id, date)
            return result, 200
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

class TesterSubjectDetailsAPI(Resource):
    """API 3: Detailed subject-based data for a tester"""
    
    def __init__(self):
        self.progress_service = ProgressService()
    
    @admin_required
    def get(self, intern_id, subject):
        """Get detailed subject data for tester"""
        date = request.args.get('date')
        if not date:
            return {"success": False, "message": "Date parameter is required"}, 400
        
        try:
            result = self.progress_service.get_tester_subject_details(intern_id, subject, date)
            return result, 200
        except Exception as e:
            return {"success": False, "message": str(e)}, 400