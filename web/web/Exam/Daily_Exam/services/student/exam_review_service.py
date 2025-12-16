"""Exam Review Service - Retrieves detailed exam analysis"""
from typing import Dict
from web.Exam.Daily_Exam.utils.analysis.score_utils import calculate_max_score_from_paper
from web.Exam.Daily_Exam.utils.exam.exam_retrieval_utils import ExamRetrievalUtils

class ExamReviewService:
    def get_exam_review(self, exam_id: str, exam_type: str) -> Dict:
        """Retrieve exam details and notAttemptedDetails by exam ID"""
        exam = ExamRetrievalUtils.get_exam_with_validation(exam_id, exam_type)
        
        analysis = exam.get("analysis", {})
        max_score = calculate_max_score_from_paper(exam.get("paper", []))
        total_score = analysis.get("totalScore", 0)
        percentage = round((total_score / max_score * 100), 1) if max_score > 0 else 0
        
        return {
            "success": True,
            "examId": exam_id,
            "maxScore": max_score,
            "totalScore": total_score,
            "percentage": percentage,
            "details": analysis.get("details", []),
            "notAttemptedDetails": analysis.get("notAttemptedDetails", [])
        }