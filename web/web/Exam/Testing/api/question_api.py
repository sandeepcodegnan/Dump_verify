"""
Question API - Refactored with Enterprise Architecture
Following SoC and DRY principles
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.question_service import QuestionService
from web.Exam.Testing.services.verification_service import VerificationService
from web.Exam.Testing.utils.formatters import format_tags
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class QuestionAPI(Resource):
    """Refactored Question CRUD API"""
    
    def __init__(self):
        self.question_service = QuestionService()
        self.verification_service = VerificationService()
        self.error_handler = ErrorHandler()
    
    @tester_required
    def get(self):
        """Get questions by filters"""
        try:
            # Validate required parameters
            subject = request.args.get("subject", "").strip().lower()
            tags_param = request.args.get("tags", "")
            intern_id = request.args.get("internId", "").strip()
            question_type = request.args.get("questionType", "").strip().lower()
            
            if not subject or not tags_param or not intern_id or not question_type:
                return self.error_handler.handle_error(ValueError("Missing required parameters"))
            
            # Pagination parameters
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, int(request.args.get("limit", 10)))
            
            tags = format_tags(tags_param)
            result = self.question_service.get_questions(subject, tags, intern_id, question_type, page, limit)
            
            # Get verification data for the intern
            verifications = self.verification_service.get_verification_history(intern_id, subject, question_type)
            
            # Create verification lookup map
            verification_map = {v["questionId"]: v for v in verifications}
            
            # Merge verification data with questions
            for question_list in [result["mcqQuestions"], result["codeQuestions"], result["queryQuestions"]]:
                for question in question_list:
                    question_id = question["questionId"]
                    verification = verification_map.get(question_id, {})
                    question["verified"] = verification.get("verified", False)
                    
                    # Add sourceCode for code questions or query for SQL questions if verified
                    if verification.get("verified"):
                        if question_type in ["code_test", "code_codeplayground_test"]:
                            question["sourceCode"] = verification.get("sourceCode")
                        elif question_type in ["query_test", "query_codeplayground_test"]:
                            question["query"] = verification.get("query")
            
            return result, 200
            
        except Exception as e:
            return self.error_handler.handle_error(e)
        
    @tester_required
    def put(self):
        """Update question"""
        try:
            body = request.get_json(silent=True) or {}
            intern_id = request.args.get("internId") or body.get("internId")
            subject = (request.args.get("subject") or 
                      body.get("Subject") or body.get("subject", "")).strip().lower()
            
            if not (intern_id and subject):
                return self.error_handler.handle_error(ValueError("Missing internId or subject"))
            
            question_id = body.get("questionId")
            if not question_id:
                return self.error_handler.handle_error(ValueError("Missing questionId"))
            
            # Update question
            updated = self.question_service.update_question(
                question_id, intern_id, subject, body
            )
            
            if updated:
                return self.error_handler.create_success_response({}, "Question updated successfully")
            else:
                return self.error_handler.handle_error(ValueError("No changes made"))
                
        except Exception as e:
            return self.error_handler.handle_error(e)
    
    @tester_required
    def delete(self):
        """Delete question"""
        try:
            # Parse request data
            if request.is_json:
                data = request.get_json(silent=True) or {}
            elif request.form:
                data = request.form.to_dict()
            else:
                data = request.args.to_dict()
            
            question_id = data.get("questionId")
            intern_id = data.get("internId", "").strip()
            subject = (data.get("Subject") or data.get("subject", "")).strip().lower()
            question_type = (data.get("Question_Type") or 
                           data.get("questionType", "")).strip().lower()
            
            if not question_id or not intern_id or not subject or not question_type:
                return self.error_handler.handle_error(ValueError("Missing required parameters"))
            
            # Delete question
            self.question_service.delete_question(
                question_id, intern_id, subject, question_type
            )
            
            return self.error_handler.create_success_response({}, "Question deleted successfully")
            
        except Exception as e:
            return self.error_handler.handle_error(e)