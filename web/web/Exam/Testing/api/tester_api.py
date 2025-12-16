"""
Tester API - Enterprise Architecture
Clean separation of concerns with service layer
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import admin_required
from web.Exam.Testing.services.tester_service import TesterService
from web.Exam.Testing.services.email_service import EmailService

class TesterAPI(Resource):
    """Refactored Tester API with enterprise architecture"""
    
    def __init__(self):
        self.tester_service = TesterService()
        self.email_service = EmailService()
    
    @admin_required
    def post(self):
        """Create new tester"""
        try:
            data = request.get_json(force=True)
            
            # Create tester
            tester_result = self.tester_service.create_tester(data)
            
            # Send welcome email asynchronously
            self.email_service.send_welcome_email_async(
                tester_result["name"],
                tester_result["email"],
                self.tester_service.get_default_password(),
                tester_result["Designation"]
            )
            
            return {
                "success": True,
                "message": "Tester signup successful",
                "tester": tester_result
            }, 201
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 400
    
    @admin_required
    def get(self):
        """Get all testers"""
        try:
            testers = self.tester_service.get_testers()
            return {"success": True, "testers": testers}, 200
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 400
    
    @admin_required
    def put(self):
        """Update tester"""
        try:
            data = request.get_json(force=True)
            tester_id = data.get("id")
            
            updated_tester = self.tester_service.update_tester(tester_id, data)
            
            return {
                "success": True,
                "message": "Tester updated successfully",
                "tester": updated_tester
            }, 200
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 400
    
    @admin_required
    def delete(self):
        """Delete tester"""
        try:
            tester_id = request.args.get("id")
            self.tester_service.delete_tester(tester_id)
            
            return {
                "success": True,
                "message": "Tester deleted successfully"
            }, 200
            
        except Exception as e:
            return {"success": False, "message": str(e)}, 400