"""
Dump Service
Business logic for question dump operations with security validation
"""
from typing import Dict, List
from datetime import datetime
from bson import ObjectId
from .base_service import BaseService
from web.Exam.Testing.config.testing_config import validate_question_type, ALLOWED_SUBJECTS
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class DumpService(BaseService):
    """Service for question dump operations"""
    
    def process_dump(self, data: Dict, page: int = 1, limit: int = 10) -> Dict:
        """Process question dump with security validation"""
        # Validate required fields
        required = ["internId", "subject", "tags", "questions"]
        InputValidator.validate_required_fields(data, required)
        
        intern_id = data["internId"]
        questions = data["questions"]
        
        if not isinstance(questions, list):
            raise ValidationError("'questions' must be a list")
        
        # Apply pagination to questions
        total_questions = len(questions)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_questions = questions[start_idx:end_idx]
        
        inserted = []
        skipped = []
        errors = []
        
        for question in paginated_questions:
            try:
                result = self._process_single_question(intern_id, question)
                if result["skipped"]:
                    skipped.append(result["question_id"])
                else:
                    inserted.append(result["inserted_id"])
            except ValidationError as e:
                errors.append(str(e))
                continue
            except Exception as e:
                errors.append(f"Error processing question: {str(e)}")
                continue
        
        # If there are validation errors, return error response
        if errors:
            return {
                "success": False,
                "message": errors[0],  # Return first error
                "status_code": 400
            }
        
        # Calculate pagination metadata
        total_pages = max(1, (total_questions + limit - 1) // limit)
        has_next = page < total_pages
        has_prev = page > 1
        
        # Build response
        response = {
            "success": True,
            "insertedCount": len(inserted),
            "insertedIds": inserted,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_questions": total_questions,
                "processed_questions": len(paginated_questions),
                "limit": limit,
                "has_next": has_next,
                "has_previous": has_prev
            }
        }
        
        if skipped:
            response.update({
                "skippedCount": len(skipped),
                "skippedIds": skipped,
                "message": f"{len(inserted)} inserted, {len(skipped)} duplicates skipped"
            })
        
        return response
    
    def _process_single_question(self, intern_id: str, question: Dict) -> Dict:
        """Process single question with security validation"""
        # Validate and normalize subject
        subject = str(question.get("Subject", "")).strip().lower()
        if not subject:
            raise ValidationError("Each question needs a non-empty Subject")
        
        # Security: Validate subject against whitelist
        if subject not in ALLOWED_SUBJECTS:
            raise ValidationError(f"Subject '{subject}' not found")
        
        # Validate and normalize question type
        question_type = str(question.get("Question_Type", "")).strip().lower()
        if not validate_question_type(question_type):
            raise ValidationError(f"Unsupported Question_Type: {question.get('Question_Type', '')}")
        
        # Security: Validate collection name
        collection_name = self._build_safe_collection_name(subject, question_type)
        
        # Check for duplicates
        question_id = question.get("questionId")
        if question_id and self._is_duplicate(collection_name, question_id):
            return {"skipped": True, "question_id": question_id}
        
        # Validate that question is verified before dumping
        if not self._is_question_verified(question_id):
            raise ValidationError(f"Question {question_id} is not verified and cannot be dumped")
        
        # Get source code for code/query questions
        source_code = self._get_source_code(question_id, question_type)
        
        # Build and insert document
        document = self._build_question_document(question, question_type, source_code)
        inserted_id = str(self.insert_one(collection_name, document))
        
        # Log dump operation
        self._log_dump_operation(intern_id, question_id, subject, question.get("Tags", ""))
        
        return {"skipped": False, "inserted_id": inserted_id}
    

    
    def _build_safe_collection_name(self, subject: str, question_type: str) -> str:
        """Build collection name with security validation"""
        # Remove '_test' suffix for collection naming
        base_type = question_type.replace("_test", "")
        collection_name = f"{subject}_{base_type}"
        
        # Additional security check
        if not all(c.isalnum() or c == '_' for c in collection_name):
            raise ValidationError("Invalid collection name characters")
        
        return collection_name
    
    def _is_duplicate(self, collection_name: str, question_id: str) -> bool:
        """Check if question already exists"""
        if not question_id:
            return False
        
        try:
            return bool(self.find_one(collection_name, {"questionId": question_id}))
        except Exception:
            return False
    
    def _is_question_verified(self, question_id: str) -> bool:
        """Check if question is verified"""
        if not question_id:
            return False
        
        try:
            qid = InputValidator.validate_object_id(question_id)
            verification = self.find_one(
                self.collections["verification"],
                {"questionId": qid},
                {"verified": 1}
            )
            return verification and verification.get("verified", False)
        except Exception:
            return False
    
    def _get_source_code(self, question_id: str, question_type: str) -> str:
        """Get source code for code/query questions"""
        if question_type not in ["code_test", "code_codeplayground_test", "query_test", "query_codeplayground_test"]:
            return ""
        
        if not question_id:
            return ""
        
        try:
            qid = InputValidator.validate_object_id(question_id)
            verification = self.find_one(
                self.collections["verification"],
                {"questionId": qid},
                {"sourceCode": 1, "query": 1}
            )
            if verification:
                if question_type in ["query_test", "query_codeplayground_test"]:
                    return verification.get("query", "")
                else:
                    return verification.get("sourceCode", "")
            return ""
        except Exception:
            return ""
    
    def _build_question_document(self, question: Dict, question_type: str, source_code: str) -> Dict:
        """Build question document for insertion"""
        # Remove internId and build base document
        document = {k: v for k, v in question.items() if k != "internId"}
        document["Question_Type"] = question_type.replace("_test", "")
        
        # Add source code for code/query questions
        if question_type in ["code_test", "code_codeplayground_test"]:
            document["sourceCode"] = source_code
        elif question_type in ["query_test", "query_codeplayground_test"]:
            document["query"] = source_code
        
        return document
    
    def _log_dump_operation(self, intern_id: str, question_id: str, subject: str, tags: str) -> None:
        """Log dump operation to tracking collection"""
        dump_log = {
            "internId": intern_id,
            "questionId": question_id,
            "subject": subject,
            "tags": str(tags).strip().lower(),
            "date": self.get_current_utc()
        }
        
        try:
            self.insert_one("internsdumped", dump_log)
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Failed to log dump operation: {str(e)}")