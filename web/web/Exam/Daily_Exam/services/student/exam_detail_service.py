"""Exam Detail Service - Get detailed exam information"""
from typing import Dict
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.formatting.json_utils import serialize_objectid
from web.Exam.Daily_Exam.utils.analysis.score_utils import calculate_max_score_from_paper
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils

class ExamDetailService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_exam_detail_by_id(self, student_id: str, exam_id: str, exam_type: str = None) -> Dict:
        """Get detailed exam data by exam ID without paper"""
        # Validate inputs at service level
        if not student_id:
            raise ValueError("stdId is required")
        if not exam_id:
            raise ValueError("examId is required")
        if not exam_type:
            raise ValueError("examType is required")
        
        # Validate exam_type
        ValidationUtils.validate_exam_type(exam_type)
        
        collections = list(ALLOWED_EXAM_TYPES)
        
        for collection in collections:
            if collection in {"Weekly-Exam", "Monthly-Exam"}:
                exam_repo = self.repo_factory.get_optimized_exam_repo(collection)
                doc = exam_repo.collection.find_one(
                    {"students.examId": exam_id, "students.studentId": student_id},
                    {"students.$": 1, "examName": 1, "startDate": 1, "totalExamTime": 1, "subjects": 1}
                )
                if doc and "students" in doc and doc["students"]:
                    student_data = doc["students"][0]
                    doc = {
                        **student_data,
                        "examName": doc["examName"],
                        "startDate": doc["startDate"],
                        "totalExamTime": doc["totalExamTime"],
                        "subjects": doc["subjects"]
                    }
            else:
                exam_repo = self.repo_factory.get_exam_repo(collection)
                projection = {"startTimestamp": 0, "submitTimestamp": 0}
                doc = exam_repo.collection.find_one({"studentId": student_id, "examId": exam_id}, projection)
            
            if doc:
                doc = serialize_objectid(doc)
                if "analysis" in doc and "details" in doc["analysis"]:
                    for detail in doc["analysis"]["details"]:
                        if "isCorrect" not in detail:
                            detail["isCorrect"] = detail.get("status") in ["Correct", "Passed"]
                
                return self._filter_exam_fields(doc, collection)
        
        raise ValueError("Exam not found")
    
    def _filter_exam_fields(self, exam_data: Dict, collection: str) -> Dict:
        """Filter exam data to return only required fields"""
        analysis = exam_data.get("analysis", {})
        return {
            "success": True,
            "examId": exam_data.get("examId"),
            "examName": exam_data.get("examName"),
            "examType": collection,
            "analysis": {
                "totalScore": analysis.get("totalScore", 0),
                "maxScore": calculate_max_score_from_paper(exam_data.get("paper", [])) or analysis.get("maxScore", 0),
                "correctCount": analysis.get("correctCount", 0),
                "incorrectCount": analysis.get("incorrectCount", 0),
                "attemptedMCQCount": analysis.get("attemptedMCQCount", 0),
                "attemptedCodeCount": analysis.get("attemptedCodeCount", 0),
                "attemptedQueryCount": analysis.get("attemptedQueryCount", 0),
                "attemptedCount": analysis.get("attemptedCount", 0),
                "totalTimeTaken": analysis.get("totalTimeTaken", 0),
                "examCompleted": analysis.get("examCompleted", False),
                "totalMCQCount": analysis.get("totalMCQCount", 0),
                "totalCodingCount": analysis.get("totalCodingCount", 0),
                "totalQueryCount": analysis.get("totalQueryCount", 0),
                "totalQuestions": analysis.get("totalQuestions", 0),
                "subjectBreakdown": analysis.get("subjectBreakdown", {}),
                "notAttemptedCount": analysis.get("notAttemptedCount", 0)
            }
        }