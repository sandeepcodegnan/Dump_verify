"""
Question Management Service
Business logic for question CRUD operations
"""
from typing import Dict, List, Optional
from bson import ObjectId
from web.Exam.Testing.services.base_service import BaseService
from web.Exam.Testing.config.testing_config import get_collection_name, validate_question_type
from web.Exam.Testing.utils.formatters import serialize_document, clean_document
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import QuestionNotFoundError, ValidationError

class QuestionService(BaseService):
    """Service for question management operations"""
    
    def get_questions(self, subject: str, tags: List[str], intern_id: str, question_type: str, page: int = 1, limit: int = 10) -> Dict:
        """Get questions by filters - filters by questionType like old code"""
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
        
        query = {"Tags": {"$in": tags}, "internId": intern_id}
        
        # Get all questions first for pagination
        all_questions = []
        
        # Filter by requested question type
        if question_type == "mcq_test":
            try:
                questions = self.find_many(f"{subject}_mcq_test", query)
                for question in questions:
                    formatted_question = serialize_document(question)
                    formatted_question["questionId"] = str(formatted_question.pop("_id"))
                    formatted_question["type"] = "mcq"
                    all_questions.append(formatted_question)
            except Exception:
                pass
                
        elif question_type == "query_test":
            try:
                questions = self.find_many(f"{subject}_query_test", query)
                for question in questions:
                    formatted_question = serialize_document(question)
                    formatted_question["questionId"] = str(formatted_question.pop("_id"))
                    formatted_question["type"] = "query"
                    if "Input" in formatted_question:
                        try:
                            formatted_question["Input_Structured"] = self._format_sql_input(formatted_question["Input"])
                        except Exception:
                            formatted_question["Input_Structured"] = {"tables": []}
                    all_questions.append(formatted_question)
            except Exception:
                pass
                
        elif question_type == "code_test":
            try:
                questions = self.find_many(f"{subject}_code_test", query)
                for question in questions:
                    formatted_question = serialize_document(question)
                    formatted_question["questionId"] = str(formatted_question.pop("_id"))
                    formatted_question["type"] = "code"
                    all_questions.append(formatted_question)
            except Exception:
                pass
                
        elif question_type == "code_codeplayground_test":
            try:
                questions = self.find_many(f"{subject}_code_codeplayground_test", query)
                for question in questions:
                    formatted_question = serialize_document(question)
                    formatted_question["questionId"] = str(formatted_question.pop("_id"))
                    formatted_question["type"] = "code"
                    all_questions.append(formatted_question)
            except Exception:
                pass
                
        elif question_type == "query_codeplayground_test":
            try:
                questions = self.find_many(f"{subject}_query_codeplayground_test", query)
                for question in questions:
                    formatted_question = serialize_document(question)
                    formatted_question["questionId"] = str(formatted_question.pop("_id"))
                    formatted_question["type"] = "query"
                    if "Input" in formatted_question:
                        try:
                            formatted_question["Input_Structured"] = self._format_sql_input(formatted_question["Input"])
                        except Exception:
                            formatted_question["Input_Structured"] = {"tables": []}
                    all_questions.append(formatted_question)
            except Exception:
                pass
        
        # Apply pagination
        total_questions = len(all_questions)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_questions = all_questions[start_idx:end_idx]
        
        # Separate by type for response
        mcq_questions = [q for q in paginated_questions if q.get("type") == "mcq"]
        code_questions = [q for q in paginated_questions if q.get("type") == "code"]
        query_questions = [q for q in paginated_questions if q.get("type") == "query"]
        
        # Remove type field
        for q_list in [mcq_questions, code_questions, query_questions]:
            for q in q_list:
                q.pop("type", None)
        
        # Calculate pagination metadata
        total_pages = max(1, (total_questions + limit - 1) // limit)
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "success": True,
            "subject": subject,
            "mcqCount": len(mcq_questions),
            "codeCount": len(code_questions),
            "queryCount": len(query_questions),
            "mcqQuestions": mcq_questions,
            "codeQuestions": code_questions,
            "queryQuestions": query_questions,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_questions": total_questions,
                "limit": limit,
                "has_next": has_next,
                "has_previous": has_prev
            }
        }
    
    def get_question_by_id(self, question_id: str, problem_type: str) -> Optional[Dict]:
        """Get single question by ID and type"""
        qid = InputValidator.validate_object_id(question_id)
        
        # Search across collections ending with problem_type
        for collection_name in self.db.list_collection_names():
            if collection_name.endswith(f"_{problem_type}"):
                question = self.find_one(collection_name, {"_id": qid})
                if question:
                    return question
        
        return None
    
    def create_question(self, question_data: Dict, subject: str) -> ObjectId:
        """Create new question"""
        InputValidator.validate_question_upload(question_data)
        
        question_type = question_data.get("Question_Type", "").lower()
        collection_name = get_collection_name(subject, question_type)
        
        # Build document based on question type
        document = self._build_question_document(question_data, question_type)
        document = clean_document(document)
        
        return self.insert_one(collection_name, document)
    
    def update_question(self, question_id: str, intern_id: str, subject: str, updates: Dict) -> bool:
        """Update existing question"""
        qid = InputValidator.validate_object_id(question_id)
        
        # Find question across collections
        for collection_name in self.db.list_collection_names():
            if collection_name.startswith(f"{subject.lower()}_"):
                existing = self.find_one(collection_name, {"_id": qid, "internId": intern_id})
                if existing:
                    # Remove fields that shouldn't be updated
                    clean_updates = {k: v for k, v in updates.items() 
                                   if k not in ["internId", "Subject", "_id", "questionId"]}
                    
                    if clean_updates:
                        return self.update_one(collection_name, {"_id": qid}, {"$set": clean_updates})
                    return True
        
        raise QuestionNotFoundError()
    
    def delete_question(self, question_id: str, intern_id: str, subject: str, question_type: str) -> bool:
        """Delete question"""
        qid = InputValidator.validate_object_id(question_id)
        
        if not validate_question_type(question_type):
            raise ValidationError(f"Invalid question type: {question_type}")
        
        collection_name = get_collection_name(subject, question_type)
        
        # Delete question
        deleted = self.delete_one(collection_name, {"_id": qid, "internId": intern_id})
        if not deleted:
            raise QuestionNotFoundError()
        
        # Clean up verification records
        self.delete_one(
            self.collections["verification"],
            {"questionId": qid, "id": intern_id}
        )
        
        return True
    
    def _build_question_document(self, data: Dict, question_type: str) -> Dict:
        """Build question document based on type"""
        base_doc = {
            "internId": data.get("internId"),
            "Question_No": data.get("Question_No"),
            "Question_Type": question_type,
            "Subject": data.get("Subject", "").lower(),
            "Question": data.get("Question", ""),
            "Score": data.get("Score"),
            "Difficulty": data.get("Difficulty", ""),
            "Tags": data.get("Tags", "").lower(),
            "Text_Explanation": data.get("Text_Explanation", ""),
            "Explanation_URL": data.get("Explanation_URL", ""),
            "Image_URL": data.get("Image_URL", "")
        }
        
        if question_type == "mcq_test":
            base_doc["Options"] = {
                "A": data.get("A", ""),
                "B": data.get("B", ""),
                "C": data.get("C", ""),
                "D": data.get("D", "")
            }
            base_doc["Correct_Option"] = data.get("Correct_Option", "")
        
        elif question_type in ["query_test", "query_codeplayground_test"]:
            base_doc["Input"] = data.get("Input", "")
            base_doc["Expected_Output"] = data.get("Expected_Output", "")
        
        elif question_type in ["code_test", "code_codeplayground_test"]:
            base_doc["Sample_Input"] = data.get("Sample_Input", "")
            base_doc["Sample_Output"] = data.get("Sample_Output", "")
            base_doc["Constraints"] = data.get("Constraints", "")
            
            # Build hidden test cases
            hidden_tests = []
            for i in range(1, 5):
                h_input = data.get(f"Hidden_Test_case_{i}_Input")
                h_output = data.get(f"Hidden_Test_case_{i}_Output")
                if h_input is not None or h_output is not None:
                    hidden_tests.append({
                        "Input": h_input or "",
                        "Output": h_output or ""
                    })
            base_doc["Hidden_Test_Cases"] = hidden_tests
        
        return base_doc
    
    def _format_sql_input(self, sql_input: str) -> Dict:
        """Format SQL input into structured data for frontend"""
        try:
            from web.Exam.mysql_templates.sql_parser import SQLParser
            
            parser = SQLParser()
            table_names = parser.extract_table_names(sql_input)
            
            tables = []
            for table_name in table_names:
                table_data = parser.parse_table(sql_input, table_name)
                
                # Convert to frontend format
                formatted_table = {
                    "name": table_name,
                    "schema": [{
                        "column": col["name"],
                        "type": f"{col['type']} {col['constraints']}".strip()
                    } for col in table_data["schema"]],
                    "data": table_data["data"]
                }
                tables.append(formatted_table)
            
            return {"tables": tables}
        
        except Exception:
            return {"tables": []}
