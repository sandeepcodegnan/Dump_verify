"""Admin Exam Toggle API - Presentation Layer"""
from web.jwt.auth_middleware import admin_required , all_access_required
from flask_restful import Resource
from web.Exam.Daily_Exam.services.admin.exam_toggle_service import ExamToggleService
from web.Exam.Daily_Exam.utils.validation.input_validator import get_json_data
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error

class ExamToggleResource(Resource):
    def __init__(self):
        self.exam_toggle_service = ExamToggleService()

    @all_access_required
    def get(self):
        """Get enabled exam types only"""
        try:
            result = self.exam_toggle_service.get_all_toggles()
            # Filter to show only enabled exam types (just the names)
            enabled_exam_types = [toggle["examType"] for toggle in result["toggles"] if toggle["isEnabled"]]
            return {"success": True, "data": enabled_exam_types}, 200
            
        except Exception as e:
            return handle_service_error(e)
    
    # @admin_required
    # def post(self):
    #     """Toggle exam on/off using body"""
    #     try:
    #         data = get_json_data()
    #         exam_type = data.get("examType")
    #         is_enabled = data.get("isEnabled", True)
            
    #         if not exam_type:
    #             return {"success": False, "message": "examType is required"}, 400
                
    #         result = self.exam_toggle_service.toggle_exam(exam_type, is_enabled)
    #         return {"success": True, "data": result}, 200
            
    #     except Exception as e:
    #         return handle_service_error(e)

class ExamToggleDetailResource(Resource):
    def __init__(self):
        self.exam_toggle_service = ExamToggleService()
    
    @admin_required
    def patch(self, exam_type):
        """Toggle exam on/off"""
        try:
            data = get_json_data()
            is_enabled = data.get("isEnabled", True)
            result = self.exam_toggle_service.toggle_exam(exam_type, is_enabled)
            return {"success": True, "data": result}, 200
            
        except Exception as e:
            return handle_service_error(e)