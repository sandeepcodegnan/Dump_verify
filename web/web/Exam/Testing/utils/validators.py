"""
Input Validators
Centralized validation logic following SoC principle
"""
from typing import Dict, List
from bson import ObjectId
from bson.errors import InvalidId
from web.Exam.Testing.config.testing_config import validate_question_type, get_required_fields
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class InputValidator:
    """Centralized input validation"""
    
    @staticmethod
    def validate_object_id(obj_id: str) -> ObjectId:
        """Validate and convert ObjectId"""
        try:
            return ObjectId(obj_id)
        except (InvalidId, TypeError):
            raise ValidationError("Invalid ObjectId format")
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> None:
        """Validate required fields are present"""
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
    
    @staticmethod
    def validate_question_data(data: Dict) -> None:
        """Validate question submission data"""
        question_type = data.get("type", "").strip().lower()
        
        # Base required fields
        required = ["internId", "question_id", "language", "type"]
        
        # Add code field based on question type
        if question_type in ["query_test", "query_codeplayground_test"]:
            required.append("query")
        else:
            required.append("source_code")
        
        InputValidator.validate_required_fields(data, required)
        
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
    
    @staticmethod
    def validate_question_upload(question: Dict) -> None:
        """Validate question upload data"""
        question_type = question.get("Question_Type", "").lower()
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
        
        required_fields = get_required_fields(question_type)
        InputValidator.validate_required_fields(question, required_fields)
        
        # Type-specific validation
        if question_type == "mcq_test" and "Score" not in question:
            raise ValidationError("MCQ questions must include 'Score'")
        
        if question_type in ["code_test", "code_codeplayground_test"]:
            if not question.get("Sample_Input") or not question.get("Sample_Output"):
                raise ValidationError("Code questions must include Sample_Input and Sample_Output")
            
            # Validate hidden test cases
            has_hidden = any(
                question.get(f"Hidden_Test_case_{i}_Input") or 
                question.get(f"Hidden_Test_case_{i}_Output")
                for i in range(1, 5)
            )
            if not has_hidden:
                raise ValidationError("Code questions must include at least one hidden test case")
    
    @staticmethod
    def validate_verification_data(data: Dict) -> None:
        """Validate verification request data"""
        required = ["internId", "questionId", "questionType", "subject", "tag"]
        InputValidator.validate_required_fields(data, required)
        
        question_type = data.get("questionType", "").strip().lower()
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
    
    @staticmethod
    def validate_test_cases(test_cases: List) -> None:
        """Validate test cases format"""
        if not isinstance(test_cases, list):
            raise ValidationError("test_cases must be a list")
        
        if not all(isinstance(tc, str) for tc in test_cases):
            raise ValidationError("All test cases must be strings")