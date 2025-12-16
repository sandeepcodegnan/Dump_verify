"""Admin Window Configuration API - Presentation Layer (SoC)"""
from web.jwt.auth_middleware import admin_required
from flask_restful import Resource
from web.Exam.Daily_Exam.services.admin.window_config_service import WindowConfigService
from web.Exam.Daily_Exam.utils.validation.input_validator import get_json_data
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error

class WindowConfigResource(Resource):
    def __init__(self):
        self.window_service = WindowConfigService()

    @admin_required
    def post(self):
        try:
            data = get_json_data()
            result = self.window_service.create_window_config(data)
            return {"success": True, "data": result}, 201
            
        except Exception as e:
            return handle_service_error(e)
    
    @admin_required
    def get(self):
        try:
            result = self.window_service.get_all_configs()
            return {"success": True, "data": result["configs"]}, 200
            
        except Exception as e:
            return handle_service_error(e)

class WindowConfigDetailResource(Resource):
    def __init__(self):
        self.window_service = WindowConfigService()
    @admin_required
    def get(self, exam_type):
        try:
            result = self.window_service.get_config_by_type(exam_type)
            return {"success": True, "data": result}, 200
            
        except Exception as e:
            return handle_service_error(e)
    @admin_required
    def put(self, exam_type):
        try:
            data = get_json_data()
            result = self.window_service.update_config(exam_type, data)
            return {"success": True, "data": result}, 200
            
        except Exception as e:
            return handle_service_error(e)
    @admin_required
    def delete(self, exam_type):
        try:
            result = self.window_service.delete_config(exam_type)
            return {"success": True, "data": result}, 200
            
        except Exception as e:
            return handle_service_error(e)