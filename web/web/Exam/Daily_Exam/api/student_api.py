from flask_restful import Resource
from web.jwt.auth_middleware import leaderbd_required, student_required
from web.Exam.Daily_Exam.services.student.start_exam_service import StartExamService
from web.Exam.Daily_Exam.services.student.available_exams_service import AvailableExamsService
from web.Exam.Daily_Exam.services.student.exam_summary_service import ExamSummaryService
from web.Exam.Daily_Exam.services.student.exam_detail_service import ExamDetailService
from web.Exam.Daily_Exam.services.student.code_execution_service import CodeExecutionService
from web.Exam.Daily_Exam.services.student.score_analysis_service import ScoreAnalysisService
from web.Exam.Daily_Exam.services.student.exam_review_service import ExamReviewService
from web.Exam.Daily_Exam.services.student.exam_dates_service import ExamDatesService
from web.Exam.Daily_Exam.services.report.leaderboard_service import LeaderboardService
from web.Exam.Daily_Exam.utils.validation.input_validator import get_json_data, get_query_params, get_default_date, get_single_query_param, get_optional_query_params
from web.Exam.Daily_Exam.utils.pagination.pagination_utils import get_pagination_params
from web.Exam.Daily_Exam.exceptions.error_handler import handle_service_error

class GetAvailableExams(Resource):
    def __init__(self):
        self.service = AvailableExamsService()            
    @student_required
    def get(self):
        try:
            params = get_query_params("studentId", "examType")            
            result = self.service.get_available_exams(params["studentId"], params["examType"])
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class StartExam(Resource):
    def __init__(self):
        self.service = StartExamService()    
    @student_required
    def post(self):
        try:
            data = get_json_data()            
            result = self.service.start_exam(data.get("examId"), data.get("collectionName"))
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class CodeExecution(Resource):
    def __init__(self):
        self.service = CodeExecutionService()    
    @student_required
    def post(self):
        try:
            data = get_json_data()
            result = self.service.execute_code(data)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class SubmitExam(Resource):
    def __init__(self):
        self.service = ScoreAnalysisService()    
    @student_required
    def post(self):
        try:
            data = get_json_data()
            result = self.service.submit_exam(data)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class ExamQuestionReview(Resource):
    def __init__(self):
        self.service = ExamReviewService()    
    @student_required
    def get(self):
        try:
            exam_id = get_single_query_param("examId")
            exam_type = get_single_query_param("examType")
            
            result = self.service.get_exam_review(exam_id, exam_type)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class StudentExamSummary(Resource):
    def __init__(self):
        self.service = ExamSummaryService()    
    @student_required
    def get(self):
        try:
            std_id = get_single_query_param("stdId")
            page = int(get_single_query_param("page") or 1)
            limit = int(get_single_query_param("limit") or 10)
            exam_type = get_single_query_param("examType")
            result = self.service.get_student_exam_summary(std_id, page, limit, exam_type)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class StudentExamDetail(Resource):
    def __init__(self):
        self.service = ExamDetailService()    
    @student_required
    def get(self):
        try:
            std_id = get_single_query_param("stdId")
            exam_id = get_single_query_param("examId")
            exam_type = get_single_query_param("examType")            
            result = self.service.get_exam_detail_by_id(std_id, exam_id, exam_type)
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class ExamBatchLeaderboard(Resource):
    def __init__(self):
        self.leaderboard_service = LeaderboardService()    
    @leaderbd_required
    def get(self):
        try:
            params = get_query_params("batch", "examType")
            optional_params = get_optional_query_params(
                date=get_default_date(),
                location=None,
                page="1",
                limit="10",
                studentId=None
            )
            
            exam_type = params["examType"]
            page, limit = get_pagination_params(optional_params["page"], optional_params["limit"])
            
            result = self.leaderboard_service.get_batch_leaderboard(
                exam_type, params["batch"], optional_params["date"], optional_params["location"], page, limit, optional_params["studentId"]
            )
            return result, 200
        except Exception as e:
            return handle_service_error(e)

class GetConductedExamDates(Resource):
    def __init__(self):
        self.service = ExamDatesService()
    @leaderbd_required
    def get(self):
        try:
            params = get_query_params("batch", "examType")
            result = self.service.get_conducted_exam_dates(params["batch"], params["examType"])
            return result, 200
        except Exception as e:
            return handle_service_error(e)