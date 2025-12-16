from flask_restful import Resource
from web.jwt.auth_middleware import manager_required
from web.Exam.Daily_Exam.utils.validation.input_validator import get_query_params
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error
from web.Exam.Interview.services.interview_service import InterviewService

class GetInterviewData(Resource):
    def __init__(self):
        self.interview_service = InterviewService()
    
    @manager_required
    def get(self):
        try:
            params = get_query_params("batch", "location")
            
            result = self.interview_service.get_curriculum_data(
                params["batch"], params["location"]
            )
            
            # Handle already exists case with 409 Conflict
            if result.get('status') == 'already_exists':
                return {
                    "success": True,
                    "message": result["message"]
                }, 409
            
            return {"success": True, **result}, 200
        except Exception as e:
            return handle_service_error(e)