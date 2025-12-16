import json
from datetime import datetime
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import student_required
from pymongo import errors
from bson import ObjectId
from web.Exam.exam_central_db import codeplayground_collection, db
from web.Exam.Flags.feature_flags import is_enabled

# ─── Helpers ────────────────────────────────────────────────────────────────────
def parse_request_data():
    if request.is_json:
        return request.get_json(force=True) or {}
    if request.form:
        return request.form.to_dict()
    return request.args.to_dict()

def error_response(message, status_code=400):
    return {"success": False, "message": message}, status_code

def serialize_datetimes(obj):
    """
    Recursively convert any datetime in obj (dict or list) to ISO strings.
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, datetime):
                obj[k] = v.isoformat() + "Z"
            else:
                serialize_datetimes(v)
    elif isinstance(obj, list):
        for item in obj:
            serialize_datetimes(item)
    # other types unchanged

# ─── Resource Definition ───────────────────────────────────────────────────────
class CpProgress(Resource):
    @student_required
    def get(self):
        if not is_enabled("flagcodePlayground"):
            return error_response("Code playground feature is disabled", 404)
            
        data = parse_request_data()

        student_id = data.get("id") or data.get("studentId")
        if not student_id:
            return error_response("'id' (or 'studentId') is required.", 400)

        # UUID validation for student_id
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, student_id.lower()):
            return error_response("Invalid student_id format. Must be UUID format.", 400)

        # Build query filter
        query_filter = {"id": student_id}
        
        # Optional questionId filter for specific submission
        question_id = data.get("questionId")
        if question_id:
            # ObjectId validation for question_id
            if not re.match(r'^[0-9a-f]{24}$', question_id.lower()):
                return error_response("Invalid questionId format. Must be 24-character ObjectId.", 400)
            query_filter["questionId"] = question_id
            # Use find_one for specific submission
            doc = codeplayground_collection.find_one(query_filter, {"_id": 0})
            if not doc:
                return error_response("No record found for that studentId and questionId.", 404)
            

            
            serialize_datetimes(doc)
            return {"success": True, "data": doc}, 200
        else:
            # Get all submissions for student
            cursor = codeplayground_collection.find(query_filter, {"_id": 0})
            docs = list(cursor)
            if not docs:
                return error_response("No records found for that studentId.", 404)
            for doc in docs:
                serialize_datetimes(doc)
            return {"success": True, "data": docs}, 200  

