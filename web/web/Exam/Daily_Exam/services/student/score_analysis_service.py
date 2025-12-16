"""Score Analysis Service - Handles exam submission and score calculation"""
from typing import Dict
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.utils.analysis.analysis_utils import (
    build_question_lookup, build_subject_breakdown, process_mcq_answer, process_coding_answer, process_query_answer
)
from web.Exam.Daily_Exam.utils.analysis.score_utils import calculate_max_score_from_paper
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.exceptions.exceptions import (
    ValidationError, ExamNotFoundError, ExamAlreadySubmittedError
)

class ScoreAnalysisService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def submit_exam(self, payload: Dict) -> Dict:
        """Submit exam and analyze scores"""
        exam_id = payload.get("examId")
        collection_name = payload.get("exam")
        
        if not exam_id or not collection_name:
            raise ValidationError("Missing examId or exam collection name.")
        
        if collection_name in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(collection_name)
            exam = exam_repo.find_student_exam_by_id(exam_id)
        else:
            exam_repo = self.repo_factory.get_exam_repo(collection_name)
            exam = exam_repo.find_by_id(exam_id)
        
        if not exam:
            raise ExamNotFoundError("Exam record not found.")
        
        if exam.get("attempt-status"):
            raise ExamAlreadySubmittedError("Exam already submitted. No further submissions allowed.")
        
        totals = exam_repo.get_exam_totals(exam_id)
        if not totals:
            raise ValidationError("Failed to calculate exam totals.")
        
        analysis = self._build_complete_analysis(payload, exam, totals)
        
        if collection_name in {"Weekly-Exam", "Monthly-Exam"}:
            success = exam_repo.submit_student_exam(exam_id, analysis)
        else:
            success = exam_repo.submit_exam(exam_id, analysis)
        
        if not success:
            raise ExamAlreadySubmittedError("Exam already submitted. No further submissions allowed.")
        
        # Calculate percentage using maxScore from exam paper
        max_score = calculate_max_score_from_paper(exam.get("paper", []))
        total_score = round(analysis["totalScore"], 1)
        percentage = round((total_score / max_score * 100), 1) if max_score > 0 else 0
        
        response_analysis = {
            "totalScore": total_score,
            "maxScore": max_score,
            "percentage": percentage,
            "correctCount": analysis["correctCount"],
            "incorrectCount": analysis["incorrectCount"],
            "attemptedMCQCount": analysis["attemptedMCQCount"],
            "attemptedCodeCount": analysis["attemptedCodeCount"],
            "attemptedQueryCount": analysis["attemptedQueryCount"],
            "attemptedCount": analysis["attemptedCount"],
            "totalTimeTaken": analysis["totalTimeTaken"],
            "examCompleted": analysis["examCompleted"],
            "totalMCQCount": analysis["totalMCQCount"],
            "totalCodingCount": analysis["totalCodingCount"],
            "totalQueryCount": analysis["totalQueryCount"],
            "totalQuestions": analysis["totalQuestions"],
            "subjectBreakdown": analysis["subjectBreakdown"],
            "notAttemptedCount": analysis["notAttemptedCount"]
        }
        
        result = {
            "success": True,
            "message": "Exam submitted successfully. No further test execution as the exam is complete.",
            "examId": exam_id,
            "examName": exam.get("examName", ""),
            "examType": collection_name,
            "analysis": response_analysis
        }
        return sanitize_mongo_document(result)
    
    def _build_complete_analysis(self, payload: Dict, exam: Dict, totals: Dict) -> Dict:
        """Build complete analysis with subject breakdown"""
        total_time_taken = payload.get("totalTimeTaken", 0)
        if total_time_taken == 0:
            raise ValidationError("Bad request: Missing Required fields or invalid data or not found.")
        
        total_mcq_count = totals["total_mcq"]
        total_code_count = totals["total_coding"]
        total_query_count = totals.get("total_query", 0)
        total_questions = total_mcq_count + total_code_count + total_query_count
        total_exam_time = totals.get("total_exam_time", 0)
        
        subject_breakdown = build_subject_breakdown(totals, total_exam_time)
        
        analysis = {
            "totalScore": 0,
            "correctCount": 0,
            "incorrectCount": 0,
            "attemptedMCQCount": 0,
            "attemptedCodeCount": 0,
            "attemptedQueryCount": 0,
            "attemptedCount": 0,
            "totalTimeTaken": total_time_taken,
            "details": [],
            "examCompleted": True,
            "totalMCQCount": total_mcq_count,
            "totalCodingCount": total_code_count,
            "totalQueryCount": total_query_count,
            "totalQuestions": total_questions,
            "subjectBreakdown": subject_breakdown,
        }
        
        question_lookup = build_question_lookup(exam.get("paper", []))
        
        attempted_ids = set()
        reserved_keys = {"examId", "exam", "totalTimeTaken", "timeTaken"}
        
        for qid, answer in payload.items():
            if qid in reserved_keys or qid not in question_lookup:
                continue
            
            qdata, qtype, subject = question_lookup[qid]
            attempted_ids.add(qid)
            analysis["attemptedCount"] += 1
            
            if qtype == "Coding":
                result = process_coding_answer(qid, answer, qdata, subject)
                analysis["attemptedCodeCount"] += 1
                if result["isCorrect"]:
                    analysis["correctCount"] += 1
                else:
                    analysis["incorrectCount"] += 1
                analysis["totalScore"] = round(analysis["totalScore"] + result["scoreAwarded"], 1)
                analysis["details"].append(result)
                self._update_subject_breakdown(analysis["subjectBreakdown"], subject, result, "coding")
            elif qtype == "Query":
                result = process_query_answer(qid, answer, qdata, subject)
                analysis["attemptedQueryCount"] += 1
                if result["isCorrect"]:
                    analysis["correctCount"] += 1
                else:
                    analysis["incorrectCount"] += 1
                analysis["totalScore"] = round(analysis["totalScore"] + result["scoreAwarded"], 1)
                analysis["details"].append(result)
                self._update_subject_breakdown(analysis["subjectBreakdown"], subject, result, "query")
            elif qtype == "MCQ":
                result = process_mcq_answer(qid, answer, qdata, subject)
                analysis["attemptedMCQCount"] += 1
                if result["isCorrect"]:
                    analysis["correctCount"] += 1
                else:
                    analysis["incorrectCount"] += 1
                analysis["totalScore"] = round(analysis["totalScore"] + result["scoreAwarded"], 1)
                analysis["details"].append(result)
                self._update_subject_breakdown(analysis["subjectBreakdown"], subject, result, "mcq")
        
        not_attempted_details = []
        for subject_paper in exam.get("paper", []):
            for mcq in subject_paper.get("MCQs", []):
                if mcq.get("questionId") not in attempted_ids:
                    not_attempted_details.append({
                        "questionId": mcq["questionId"],
                        "question": mcq.get("Question"),
                        "options": mcq.get("Options") or {},
                        "correctAnswer": mcq.get("Correct_Option"),
                    })
            for coding in subject_paper.get("Coding", []):
                if coding.get("questionId") not in attempted_ids:
                    not_attempted_details.append({
                        "questionId": coding["questionId"],
                        "question": coding.get("Question"),
                    })
            for query in subject_paper.get("Query", []):
                if query.get("questionId") not in attempted_ids:
                    not_attempted_details.append({
                        "questionId": query["questionId"],
                        "question": query.get("Question"),
                    })
        
        analysis["notAttemptedCount"] = len(not_attempted_details)
        analysis["notAttemptedDetails"] = not_attempted_details
        
        return analysis
    
    def _update_subject_breakdown(self, subject_breakdown: Dict, subject: str, result: Dict, question_type: str):
        """Update subject breakdown with answer result"""
        if subject in subject_breakdown:
            sb = subject_breakdown[subject]
            sb["attempted"] += 1
            sb["unattempted"] -= 1
            score_awarded = round(result["scoreAwarded"], 1)
            sb["score"] = round(sb["score"] + score_awarded, 1)
            sb[question_type]["attempted"] += 1
            sb[question_type]["score"] = round(sb[question_type]["score"] + score_awarded, 1)