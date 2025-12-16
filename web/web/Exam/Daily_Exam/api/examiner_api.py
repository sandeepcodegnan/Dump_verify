"""Examiner API - Presentation Layer (SoC)"""
from flask_restful import Resource
from web.jwt.auth_middleware import exams_required, manager_required
from web.Exam.Daily_Exam.services.examiner.check_exam_status_service import CheckExamStatusService
from web.Exam.Daily_Exam.services.examiner.exam_data_service import ExamDataService
from web.Exam.Daily_Exam.services.examiner.generate_exam_service import GenerateExamService
from web.Exam.Daily_Exam.services.examiner.exam_day_list_service import ExamDayListService
from web.Exam.Daily_Exam.services.report.report_service import ReportService
from web.Exam.Daily_Exam.external.whatsapp_client import WhatsAppClient
from web.Exam.Daily_Exam.utils.validation.input_validator import get_json_data, get_query_params, get_single_query_param
from web.Exam.Daily_Exam.utils.pagination.pagination_utils import get_pagination_params
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error

class CheckExamStatus(Resource):
    def __init__(self):
        self.service = CheckExamStatusService()
    
    @manager_required
    def get(self):
        try:
            params = get_query_params("examType", "location", "date")
            page, limit = get_pagination_params(
                get_single_query_param("page", required=False),
                get_single_query_param("limit", required=False)
            )
            
            result = self.service.check_batches_status(params["examType"], params["location"], params["date"], page, limit)
            
            return result, 200
        except Exception as e:
            return handle_service_error(e)
        
class GetExamData(Resource):
    def __init__(self):
        self.service = ExamDataService()
    
    @manager_required
    def post(self):
        try:
            data = get_json_data()
            
            result = self.service.get_curriculum_data(data["date"], data["batch"], data["location"], data["examType"], data["subjects"])
            
            return result, 200
        except Exception as e:
            return handle_service_error(e)

     

class GenerateExamPaper(Resource):
    def __init__(self):
        self.service = GenerateExamService()
        self.whatsapp_client = WhatsAppClient()
    
    @manager_required
    def post(self):
        try:
            data = get_json_data()
            result, notification_data = self.service.generate(data)
            
            self.whatsapp_client.send_exam_notifications(notification_data)
            
            return {"success": True, "data": result}, 201
        except Exception as e:
            return handle_service_error(e)

class ExaminerExamDayList(Resource):
    def __init__(self):
        self.service = ExamDayListService()
    
    @exams_required
    def get(self):
        try:
            params = get_query_params("batch", "location")
            exam_type = get_single_query_param("examType", required=False) or "Daily-Exam"
            
            result = self.service.get_list(params["batch"], params["location"], exam_type)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class ExaminerBatchReports(Resource):
    def __init__(self):
        self.report_service = ReportService()
    
    @exams_required
    def get(self):
        try:
            params = get_query_params("batch", "examName")
            exam_name = params.get("examName")
            exam_type = get_single_query_param("examType", required=False) or "Daily-Exam"
            search = get_single_query_param("search", required=False)
            attempted = get_single_query_param("attempted", required=False)
            sort_by = get_single_query_param("sortBy", required=False)
            sort_order = get_single_query_param("sortOrder", required=False) or "desc"
            export_format = get_single_query_param("export", required=False)
            
            if export_format == "excel":
                result = self.report_service.export_batch_reports_excel(exam_type, params["batch"], exam_name, search, attempted, sort_by, sort_order)
                return result
            else:
                page, limit = get_pagination_params(
                    get_single_query_param("page", required=False),
                    get_single_query_param("limit", required=False)
                )
                result = self.report_service.get_batch_reports(exam_type, params["batch"], exam_name, page, limit, search, attempted, sort_by, sort_order)
                return result, 200
        except Exception as e:
            return handle_service_error(e)