from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import exams_required
from web.Exam.exam_statistics.shared.exam_report_service import ExamReportService
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.exam_central_db import db

class BatchReport(Resource):
    def __init__(self):
        self.service = ExamReportService()
    
    @exams_required
    def get(self):
        batch_param = request.args.get("batch")
        if not batch_param:
            return {"error": "Missing `batch` parameter."}, 400
        
        try:
            params = self.service.validate_and_parse_params(
                request.args.get("date"),
                request.args.get("examType", "Daily-Exam"),
                request.args.get("location"),
                batch_param
            )
        except ValueError as e:
            return {"error": str(e)}, 400

        repo = self.service.get_repository(params["exam_type"])
        return (self._get_optimized_report(repo, params) 
                if params["exam_type"] in {"Weekly-Exam", "Monthly-Exam"} 
                else self._get_legacy_report(repo, params))
    
    def _get_legacy_report(self, repo, params):
        query = self.service.build_query(params["date_key"], params["location_param"], params["batch_param"])
        allocated, attempted = self.service.get_basic_counts(repo, query)
        
        exam_doc = repo.collection.find_one(query, {"windowEndTime": 1, "totalExamTime": 1, "examName": 1})
        last_end_time = (self.service.calculate_end_time(exam_doc.get("windowEndTime"), exam_doc.get("totalExamTime")) 
                        if exam_doc else None)
        
        return self._build_response(params, allocated, attempted, last_end_time, query, exam_doc.get("examName") if exam_doc else None)
    
    def _get_optimized_report(self, repo, params):
        query = self.service.build_query(params["date_key"], params["location_param"], params["batch_param"])
        exam_doc = repo.collection.find_one(query)
        
        if not exam_doc:
            return self._build_response(params, 0, 0, None, {})
        
        students_data = exam_doc.get("students", [])
        allocated = len(students_data)
        attempted = sum(1 for s in students_data if s.get("attempt-status"))
        last_end_time = self.service.calculate_end_time(exam_doc.get("windowEndTime"), exam_doc.get("totalExamTime"))
        
        student_ids = [s["studentId"] for s in students_data]
        query_for_students = {"id": {"$in": student_ids}}
        if params["location_param"]:
            query_for_students["location"] = params["location_param"]
            
        return self._build_response(params, allocated, attempted, last_end_time, query_for_students, exam_doc.get("examName"))
    
    def _build_response(self, params, allocated: int, attempted: int, last_end_time: str, student_query: dict, exam_name: str = None):
        students = (list(db["student_login_details"].find(
            student_query, {"_id": 0, "id": 1, "name": 1, "studentPhNumber": 1}
        )) if student_query else [])
        
        # Fallback for Daily-Exam
        if not students and params["exam_type"] == "Daily-Exam":
            exam_repo = self.service.get_repository(params["exam_type"])
            exam_students = list(exam_repo.collection.find(
                {"startDate": params["date_key"], "batch": params["batch_param"]}, 
                {"_id": 0, "studentId": 1}
            ))
            if exam_students:
                student_ids = [s["studentId"] for s in exam_students]
                students = self.service.get_students_by_ids(student_ids)
        
        wa_stats = self.service.get_whatsapp_stats(params["date_key"], params["batch_param"])
        merged_students = self.service.merge_student_data(students, wa_stats)

        result = {
            "exam_type": params["exam_type"],
            "date": params["date_key"],
            "batch": params["batch_param"],
            "location": params["location_param"],
            "allocated": allocated,
            "attempted": attempted,
            "not_attempted": allocated - attempted,
            "last_exam_end_time": last_end_time,
            "students": merged_students,
        }
        
        if exam_name:
            result["exam_name"] = exam_name
        
        return sanitize_mongo_document(result)