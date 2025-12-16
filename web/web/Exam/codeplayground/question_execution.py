from flask import request, jsonify
from flask_restful import Resource
from web.jwt.auth_middleware import student_required
from pymongo import errors
from bson import ObjectId
from web.Exam.exam_central_db import db
from web.Exam.Flags.feature_flags import is_enabled

def parse_request_data():
    if request.is_json:
        return request.get_json(force=True)
    if request.form:
        return request.form.to_dict()
    return request.args.to_dict()

def error_response(message, status_code=400):
    resp = jsonify({"success": False, "message": message})
    resp.status_code = status_code
    return resp

class QuestionExecution(Resource):
    @student_required
    def get(self):
        if not is_enabled("flagcodePlayground"):
            return error_response("Code playground feature is disabled", 404)
            
        data = parse_request_data()  # request data gets parsed (for example, query params)
        question_id = data.get("questionId", "").strip()
        subject = data.get("subject", "").strip().lower()

        if not question_id:
            return error_response("'questionId' is required.", 400)
        if not subject:
            return error_response("'subject' is required.", 400)

        try:
            obj_id = ObjectId(question_id)  # Convert string to MongoDB ObjectId
        except:
            return error_response("Invalid questionId format.", 400)

        # Access the collection based on the subject
        code_coll = f"{subject}_code_codeplayground"

        # Query database to fetch the question data
        try:
            question = db[code_coll].find_one({"_id": obj_id})
        except errors.PyMongoError:
            return error_response("Database error.", 500)

        if not question:
            return error_response("Question not found.", 404)

        # Return only the safe data (no hidden test cases)
        return {
            "success": True,
            "questionId": question_id,
            "Question": question.get("Question", ""),
            "Sample_Input": question.get("Sample_Input", ""),
            "Sample_Output": question.get("Sample_Output", ""),
            "Constraints": question.get("Constraints", ""),
            "Score": question.get("Score", 0),
            "Difficulty": question.get("Difficulty", ""),
            "totalTestCases": 1 + len(question.get("Hidden_Test_Cases", [])),
            "Question_No":question.get("Question_No","")
        }, 200
