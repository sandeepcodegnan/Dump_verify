"""Mentor API - Presentation Layer (SoC)"""
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from web.Exam.Daily_Exam.services.mentor.exam_list_service import ExamListService
from web.Exam.Daily_Exam.utils.validation.input_validator import get_query_params, parse_subjects_filter, get_single_query_param
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error

class MentorExamDayList(Resource):
    def __init__(self):
        self.service = ExamListService()
    
    @mentor_required
    def get(self):
        try:
            params = get_query_params("batch")
            subjects = parse_subjects_filter()
            exam_type = get_single_query_param("examType", required=False) or "Daily-Exam"
            
            result = self.service.get_list(params["batch"], subjects, exam_type)
            
            return result, 200
        except Exception as e:
            return handle_service_error(e)