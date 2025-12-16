"""
Upload Service
Business logic for question upload with S3 integration
"""
import os
import uuid
import boto3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from .base_service import BaseService
from .verification_service import VerificationService
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.utils.formatters import clean_document
from web.Exam.Testing.config.testing_config import get_collection_name, validate_question_type
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError, ExecutionError

class UploadService(BaseService):
    """Service for question upload operations"""
    
    def __init__(self):
        super().__init__()
        self.verification_service = VerificationService()
        self._init_s3_client()
    
    def upload_questions(self, file_data: Optional[bytes], questions_data: str) -> Dict:
        """Upload questions with optional cover image"""
        # Handle file upload
        image_url = self._upload_cover_image(file_data) if file_data else None
        
        # Parse and validate questions
        questions = self._parse_questions_data(questions_data)
        
        # Process questions
        results = self._process_questions(questions, image_url)
        
        # Generate summary statistics
        summary = self._generate_summary_stats(results)
        
        return {
            "success": True,
            "message": "Questions uploaded and creation logged.",
            **summary
        }
    
    def _init_s3_client(self) -> None:
        """Initialize S3 client with error handling"""
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
            self.s3_bucket = os.getenv("S3_BUCKET_QUESTION_IMAGES")
            
            if not all([os.getenv("AWS_ACCESS_KEY_ID"), os.getenv("AWS_SECRET_ACCESS_KEY"), 
                       os.getenv("AWS_REGION"), self.s3_bucket]):
                raise ExecutionError("AWS S3 configuration incomplete")
                
        except Exception as e:
            raise ExecutionError(f"S3 client initialization failed: {str(e)}")
    
    def _upload_cover_image(self, file_data: bytes) -> str:
        """Upload cover image to S3"""
        try:
            # Generate secure filename
            file_extension = ".jpg"  # Default extension
            key = f"cover-images/{uuid.uuid4()}{file_extension}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=file_data,
                ContentType="image/jpeg"
            )
            
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{key}"
            
        except Exception as e:
            raise ExecutionError(f"S3 upload failed: {str(e)}")
    
    def _parse_questions_data(self, questions_data: str) -> List[Dict]:
        """Parse and validate questions data"""
        import json
        
        try:
            payload = json.loads(questions_data) if questions_data else []
        except (json.JSONDecodeError, ValueError):
            raise ValidationError("Invalid JSON in questions data")
        
        questions = payload if isinstance(payload, list) else [payload]
        if not questions:
            raise ValidationError("Expected a question object or a list")
        
        return questions
    
    def _process_questions(self, questions: List[Dict], image_url: Optional[str]) -> List[Dict]:
        """Process and insert questions"""
        results = []
        
        for question in questions:
            try:
                result = self._process_single_question(question, image_url)
                results.append(result)
            except Exception as e:
                # Log error but continue with other questions
                print(f"Error processing question: {str(e)}")
                continue
        
        return results
    
    def _process_single_question(self, question: Dict, image_url: Optional[str]) -> Dict:
        """Process single question"""
        # Validate question
        self._validate_question(question)
        
        # Extract metadata
        intern_id = question["internId"]
        question_type = question["Question_Type"].lower()
        subject = question["Subject"].lower()
        tag = question.get("Tags", "").lower()
        
        # Build document
        document = self._build_question_document(question, question_type, image_url)
        
        # Insert into collection
        collection_name = get_collection_name(subject, question_type)
        question_id = self.insert_one(collection_name, document)
        
        # Create verification record
        self.verification_service.create_verification_record(
            intern_id, question_id, question_type, subject, tag
        )
        
        return {
            "intern_id": intern_id,
            "question_type": question_type,
            "subject": subject,
            "tag": tag,
            "question_id": question_id
        }
    
    def _validate_question(self, question: Dict) -> None:
        """Validate question data"""
        # Basic validation
        if not question.get("internId"):
            raise ValidationError("Missing 'internId' field")
        
        question_type = question.get("Question_Type", "").lower()
        if not question_type.endswith("_test"):
            raise ValidationError("Question_Type must end with '_test'")
        
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
        
        if not question.get("Subject"):
            raise ValidationError("Missing 'Subject' field")
        
        # Type-specific validation
        if question_type == "mcq_test":
            if "Score" not in question:
                raise ValidationError("MCQ questions must include 'Score'")
        
        elif question_type in ["query_test", "query_codeplayground_test"]:
            required = ["Input", "Expected_Output", "Question", "Score", "Difficulty", "Tags"]
            for field in required:
                if not question.get(field):
                    raise ValidationError(f"Query questions must include '{field}' field")
        
        elif question_type in ["code_test", "code_codeplayground_test"]:
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
    
    def _build_question_document(self, question: Dict, question_type: str, image_url: Optional[str]) -> Dict:
        """Build question document for insertion"""
        base_doc = {
            "internId": question["internId"],
            "Question_No": question.get("Question_No"),
            "Question_Type": question_type,
            "Subject": question["Subject"].lower(),
            "Question": question.get("Question", ""),
            "Score": question.get("Score"),
            "Difficulty": question.get("Difficulty", ""),
            "Tags": question.get("Tags", "").lower(),
            "Text_Explanation": question.get("Text_Explanation", ""),
            "Explanation_URL": question.get("Explanation_URL", ""),
            "Image_URL": image_url or question.get("Image_URL", "")
        }
        
        # Type-specific fields
        if question_type == "mcq_test":
            base_doc["Options"] = {
                "A": question.get("A", ""),
                "B": question.get("B", ""),
                "C": question.get("C", ""),
                "D": question.get("D", "")
            }
            base_doc["Correct_Option"] = question.get("Correct_Option", "")
        
        elif question_type in ["query_test", "query_codeplayground_test"]:
            base_doc.update({
                "Input": question.get("Input", ""),
                "Expected_Output": question.get("Expected_Output", "")
            })
        
        elif question_type in ["code_test", "code_codeplayground_test"]:
            base_doc.update({
                "Sample_Input": question.get("Sample_Input", ""),
                "Sample_Output": question.get("Sample_Output", ""),
                "Constraints": question.get("Constraints", ""),
                "Hidden_Test_Cases": self._build_hidden_test_cases(question)
            })
        
        return clean_document(base_doc)
    
    def _build_hidden_test_cases(self, question: Dict) -> List[Dict]:
        """Build hidden test cases array"""
        hidden_tests = []
        for i in range(1, 5):
            h_input = question.get(f"Hidden_Test_case_{i}_Input")
            h_output = question.get(f"Hidden_Test_case_{i}_Output")
            if h_input is not None or h_output is not None:
                hidden_tests.append({
                    "Input": h_input or "",
                    "Output": h_output or ""
                })
        return hidden_tests
    
    def _generate_summary_stats(self, results: List[Dict]) -> Dict:
        """Generate summary statistics"""
        if not results:
            return {}
        
        # Get last processed question for stats
        last_result = results[-1]
        intern_id = last_result["intern_id"]
        subject = last_result["subject"]
        tag = last_result["tag"]
        
        # Calculate date range for today
        now = self.get_current_utc()
        today = now.date()
        start_of_day = datetime(today.year, today.month, today.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Count questions by type for this tag
        tag_counts = self._count_questions_by_tag(intern_id, subject, tag)
        
        # Count questions created today
        today_counts = self._count_questions_today(intern_id, start_of_day, end_of_day)
        
        return {
            **tag_counts,
            **today_counts
        }
    
    def _count_questions_by_tag(self, intern_id: str, subject: str, tag: str) -> Dict:
        """Count questions by tag"""
        counts = {}
        for qtype in ["mcq_test", "code_test", "code_codeplayground_test", "query_test", "query_codeplayground_test"]:
            key = qtype.replace("_test", "").replace("_", "")
            if qtype == "code_codeplayground_test":
                key = "code"  # Combine code types for summary
            
            count_key = f"{key}CreatedForTag"
            if count_key not in counts:
                counts[count_key] = 0
            
            counts[count_key] += self.count_documents(
                self.collections["verification"],
                {
                    "id": intern_id,
                    "questionType": qtype,
                    "subject": subject,
                    "tag": tag
                }
            )
        
        return counts
    
    def _count_questions_today(self, intern_id: str, start_of_day: datetime, end_of_day: datetime) -> Dict:
        """Count questions created today"""
        base_query = {
            "id": intern_id,
            "createdAt": {"$gte": start_of_day, "$lt": end_of_day}
        }
        
        return {
            "internCreatedOnDate": self.count_documents(self.collections["verification"], base_query),
            "mcqCreatedOnDate": self.count_documents(
                self.collections["verification"], 
                {**base_query, "questionType": "mcq_test"}
            ),
            "codeCreatedOnDate": self.count_documents(
                self.collections["verification"],
                {**base_query, "questionType": {"$in": ["code_test", "code_codeplayground_test"]}}
            ),
            "queryCreatedOnDate": self.count_documents(
                self.collections["verification"],
                {**base_query, "questionType": {"$in": ["query_test", "query_codeplayground_test"]}}
            )
        }