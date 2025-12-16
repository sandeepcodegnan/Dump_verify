from flask import request, jsonify
from web.jwt.auth_middleware import student_required
from flask_restful import Resource
from pymongo import errors
from web.Exam.exam_central_db import db, codeplayground_collection
from web.Exam.Flags.feature_flags import is_enabled
import re

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

class QuestionsWithProgress(Resource):
    """
    Combined API: Questions + Student Progress
    GET /api/v1/questions-with-progress
    Query parameters:
      - subject: required
      - tags: required, comma-separated
      - studentId: required for progress data
    """
    @student_required
    def get(self):
        if not is_enabled("flagcodePlayground"):
            return error_response("Code playground feature is disabled", 404)
            
        data = parse_request_data()
        subject = data.get("subject", "").strip().lower()
        tags_str = data.get("tags", "")
        student_id = data.get("studentId", "").strip()
        page = data.get("page")
        limit = data.get("limit")
        
        # Convert to int if provided
        try:
            page = int(page) if page else None
            limit = int(limit) if limit else None
        except (ValueError, TypeError):
            return error_response("'page' and 'limit' must be valid integers.", 400)
        tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]

        if not all([subject, tags, student_id, page, limit]):
            return error_response("'subject', 'tags', 'studentId', 'page', and 'limit' are required.", 400)
        
        # Pagination validation
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10
            
        skip = (page - 1) * limit

        # UUID validation
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, student_id.lower()):
            return error_response("Invalid studentId format.", 400)

        # Get questions
        code_coll = f"{subject}_code_codeplayground"
        tag_patterns = [f"^{tag}$" for tag in tags]
        query = {"Tags": {"$regex": "|".join(tag_patterns), "$options": "i"}}

        try:
            code_qs = list(db[code_coll].find(query))
        except errors.PyMongoError:
            code_qs = []

        # Get student progress for these questions
        question_ids = [str(q["_id"]) for q in code_qs]
        progress_data = {}
        
        if question_ids:
            cursor = codeplayground_collection.find(
                {"id": student_id, "questionId": {"$in": question_ids}},
                {"_id": 0, "questionId": 1, "awarded_score": 1, "max_score": 1, 
                 "overall_performance": 1, "results": 1, "time_tracking": 1}
            )
            for doc in cursor:
                qid = doc.get("questionId")
                results = doc.get("results", [])
                passed_count = sum(1 for r in results if r.get("status") == "Passed")
                total_testcases = len([r for r in results if r.get("type") in ("sample", "hidden")])
                
                perf = doc.get("overall_performance", {})
                tracking = doc.get("time_tracking", {})
                
                progress_data[qid] = {
                    "awarded_score": doc.get("awarded_score", 0),
                    "max_score": doc.get("max_score", 0),
                    "status": tracking.get("status", "Not Started"),
                    "total_execution_time": perf.get("total_execution_time", "0ms"),
                    "testcases_passed": passed_count,
                    "total_testcases": total_testcases,
                    "is_solved": doc.get("awarded_score", 0) == doc.get("max_score", 0),
                    "total_time_spent": tracking.get("total_time_spent", 0),
                    "max_memory_used": perf.get("max_memory_used", "0KB")
                }

        # Combine questions with progress (all questions for summary)
        all_questions = []
        for q in code_qs:
            qid = str(q["_id"])
            hidden_count = len(q.get("Hidden_Test_Cases", []))
            total_test_cases = 1 + hidden_count
            
            progress = progress_data.get(qid, {
                "awarded_score": 0,
                "max_score": q.get("Score", 0),
                "status": "Not Started",
                "total_execution_time": "0ms",
                "testcases_passed": 0,
                "total_testcases": total_test_cases,
                "is_solved": False,
                "total_time_spent": 0,
                "max_memory_used": "0KB"
            })
            
            all_questions.append({
                "questionId": qid,
                "Question": q.get("Question", ""),
                "Score": q.get("Score", 0),
                "Difficulty": q.get("Difficulty", ""),
                "Question_No": q.get("Question_No", 0),
                "totalTestCases": total_test_cases,
                "progress": progress
            })

        # Sort questions by Question_No for consistent pagination
        all_questions.sort(key=lambda x: x.get("Question_No", 0))
        
        # Apply pagination
        total_questions = len(all_questions)
        total_pages = (total_questions + limit - 1) // limit
        paginated_questions = all_questions[skip:skip + limit]
        
        # Summary stats (from all questions)
        solved_count = sum(1 for q in all_questions if q["progress"]["is_solved"])
        attempted_count = sum(1 for q in all_questions if q["progress"]["status"] != "Not Started")
        
        return {
            "success": True,
            "subject": subject,
            "tags": tags,
            "studentId": student_id,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_questions,
                "per_page": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "summary": {
                "total_questions": total_questions,
                "solved": solved_count,
                "attempted": attempted_count,
                "not_started": total_questions - attempted_count
            },
            "questions": paginated_questions
        }, 200