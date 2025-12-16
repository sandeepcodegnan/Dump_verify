"""Question Repository - Data Access Layer (SoC) - Optimized Implementation"""
from typing import List, Dict
from web.Exam.exam_central_db import get_db
from web.Exam.Daily_Exam.repositories.question.question_pipelines import build_question_fetch_pipeline

class QuestionRepo:
    def __init__(self, subject: str):
        from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
        
        db = get_db()
        self.subject = subject.lower()
        self.mcq_collection = db[f"{self.subject}_mcq"]
        
        # Check if SQL subject for query questions
        self.is_sql_subject = self.subject in SQL_SUBJECTS
        
        if self.is_sql_subject:
            self.query_collection = db[f"{self.subject}_query"]
        else:
            self.code_collection = db[f"{self.subject}_code"]
    
    def fetch_questions_batch(self, mcq_config: Dict, second_config: Dict) -> Dict:
        """Single query to fetch MCQ and coding/query questions eliminating N+1 queries"""
        if self.is_sql_subject:
            results = {"mcq": [], "query": []}
            
            if mcq_config.get("amount", 0) > 0:
                mcq_pipeline = build_question_fetch_pipeline(
                    mcq_config["tags"], mcq_config["difficulty"], mcq_config["amount"]
                )
                results["mcq"] = list(self.mcq_collection.aggregate(mcq_pipeline))
            
            if second_config.get("amount", 0) > 0:
                query_pipeline = build_question_fetch_pipeline(
                    second_config["tags"], second_config["difficulty"], second_config["amount"]
                )
                results["query"] = list(self.query_collection.aggregate(query_pipeline))
        else:
            results = {"mcq": [], "code": []}
            
            if mcq_config.get("amount", 0) > 0:
                mcq_pipeline = build_question_fetch_pipeline(
                    mcq_config["tags"], mcq_config["difficulty"], mcq_config["amount"]
                )
                results["mcq"] = list(self.mcq_collection.aggregate(mcq_pipeline))
            
            if second_config.get("amount", 0) > 0:
                code_pipeline = build_question_fetch_pipeline(
                    second_config["tags"], second_config["difficulty"], second_config["amount"]
                )
                results["code"] = list(self.code_collection.aggregate(code_pipeline))
        
        return results
    

    def get_hidden_tests(self, question_id: str) -> List[Dict]:
        """Get hidden test cases for a specific question"""
        from bson import ObjectId
        
        try:
            if self.is_sql_subject:
                # For SQL subjects, get from query collection
                question = self.query_collection.find_one(
                    {"_id": ObjectId(question_id)},
                    {"Hidden_Test_Cases": 1}
                )
            else:
                # For coding subjects, get from code collection
                question = self.code_collection.find_one(
                    {"_id": ObjectId(question_id)},
                    {"Hidden_Test_Cases": 1}
                )
            return question.get("Hidden_Test_Cases", []) if question else []
        except:
            return []