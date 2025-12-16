"""
Verification API - Refactored with Enterprise Architecture
Following SoC and DRY principles
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.verification_service import VerificationService
from web.Exam.Testing.exceptions.testing_exceptions import ErrorHandler

class VerificationAPI(Resource):
    """Refactored Question Verification API"""
    
    def __init__(self):
        self.verification_service = VerificationService()
        self.error_handler = ErrorHandler()
    
    @tester_required
    def put(self):
        """Verify/unverify question"""
        try:
            data = request.get_json(silent=True) or {}
            
            intern_id = data.get("internId")
            question_id = data.get("questionId")
            
            if not intern_id or not question_id:
                return self.error_handler.handle_error(ValueError("Missing internId or questionId"))
            question_type = data.get("questionType", "").strip().lower()
            subject = data.get("subject", "").strip().lower()
            tag = data.get("tag", "").strip()
            verified = bool(data.get("verified", True))
            
            # Check if question is already verified
            existing_verification = self.verification_service.get_verification_history(intern_id, subject, question_type)
            existing = next((v for v in existing_verification if v["questionId"] == question_id), None)
            
            if existing and existing.get("verified") == verified:
                message = "This question is already verified" if verified else "This question is already unverified"
                return {
                    "success": True,
                    "message": message,
                    "verification": existing
                }, 200
            
            # Get appropriate code field based on question type
            if question_type in ["query_test", "query_codeplayground_test"]:
                source_code = data.get("query")
            else:
                source_code = data.get("sourceCode")
            
            result = self.verification_service.verify_question(
                intern_id, question_id, question_type, subject, tag, verified, source_code
            )
            
            return {
                "success": True,
                "verification": result
            }, 200
            
        except Exception as e:
            return self.error_handler.handle_error(e)
    
