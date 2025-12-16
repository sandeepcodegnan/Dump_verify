"""Exam Summary Service - Get paginated exam summaries"""
from typing import Dict
from web.Exam.Daily_Exam.config.settings import ALLOWED_EXAM_TYPES
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.formatting.json_utils import serialize_objectid
from web.Exam.Daily_Exam.utils.analysis.score_utils import calculate_max_score_from_subjects, calculate_max_score_from_paper

class ExamSummaryService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_student_exam_summary(self, student_id: str, page: int = 1, limit: int = 10, exam_type: str = None) -> Dict:
        """Get minimal exam summary with pagination"""
        if exam_type:
            from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils
            exam_type = ValidationUtils.validate_exam_type(exam_type)
        
        collections = [exam_type] if exam_type else list(ALLOWED_EXAM_TYPES)
        results = {}
        skip = (page - 1) * limit
        
        for collection in collections:
            if collection in {"Weekly-Exam", "Monthly-Exam"}:
                exam_repo = self.repo_factory.get_optimized_exam_repo(collection)
                pipeline = [
                    {"$match": {"students.studentId": student_id}},
                    {"$unwind": "$students"},
                    {"$match": {"students.studentId": student_id}},
                    {"$project": {
                        "examName": 1, "examId": "$students.examId",
                        "subjects": 1, "analysis": "$students.analysis",
                        "attempt-status": "$students.attempt-status"
                    }},
                    {"$sort": {"_id": -1}},
                    {"$skip": skip},
                    {"$limit": limit}
                ]
                documents = list(exam_repo.collection.aggregate(pipeline))
                
                count_pipeline = [
                    {"$match": {"students.studentId": student_id}},
                    {"$unwind": "$students"},
                    {"$match": {"students.studentId": student_id}},
                    {"$count": "total"}
                ]
                count_result = list(exam_repo.collection.aggregate(count_pipeline))
                total_count = count_result[0]["total"] if count_result else 0
            else:
                exam_repo = self.repo_factory.get_exam_repo(collection)
                projection = {
                    "examName": 1, "examId": 1,
                    "subjects": 1, "paper": 1, "analysis.totalScore": 1, "attempt-status": 1
                }
                total_count = exam_repo.collection.count_documents({"studentId": student_id})
                documents = list(exam_repo.collection.find(
                    {"studentId": student_id}, projection
                ).sort("_id", -1).skip(skip).limit(limit))
            
            summary_list = []
            for doc in documents:
                if not doc:
                    continue
                    
                doc = serialize_objectid(doc)
                
                # Use paper-based calculation if available, fallback to subjects
                paper = doc.get("paper", [])
                if paper:
                    max_score = calculate_max_score_from_paper(paper)
                else:
                    max_score = calculate_max_score_from_subjects(doc.get("subjects", []))
                analysis = doc.get("analysis") or {}
                total_score = analysis.get("totalScore", 0) if isinstance(analysis, dict) else 0
                percentage = round((total_score / max_score * 100), 1) if max_score > 0 else 0
                
                summary_list.append({
                    "examId": doc.get("examId") or "",
                    "examName": doc.get("examName") or "",
                    "totalScore": total_score,
                    "maxScore": max_score,
                    "percentage": percentage,
                    "scoreDisplay": f"{total_score}/{max_score}",
                    "attemptStatus": doc.get("attempt-status", False)
                })
            
            results[collection] = {
                "data": summary_list,
                "pagination": {
                    "currentPage": page,
                    "totalPages": (total_count + limit - 1) // limit,
                    "totalItems": total_count,
                    "itemsPerPage": limit,
                    "hasNext": page * limit < total_count,
                    "hasPrev": page > 1
                }
            }
        
        return {"success": True, "results": results}