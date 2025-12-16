"""Score calculation utilities for exam analysis"""
from typing import Dict, List
from web.Exam.Daily_Exam.config.settings import DEFAULT_MCQ_SCORE, DIFFICULTY_SCORES, DEFAULT_DIFFICULTY_SCORE

def get_question_score(question: Dict, question_type: str) -> int:
    """Get score for a question with fallback logic"""
    # Check for Score field first (capital S)
    if "Score" in question:
        return question["Score"]
    if "score" in question:
        return question["score"]
    
    if question_type == "mcq":
        return DEFAULT_MCQ_SCORE
    
    # For coding/query questions, check Difficulty field (capital D) first
    difficulty = question.get("Difficulty", question.get("difficulty", "easy")).lower()
    return DIFFICULTY_SCORES.get(difficulty, DEFAULT_DIFFICULTY_SCORE)

def calculate_max_score_from_paper(exam_paper: List[Dict]) -> int:
    """Calculate maximum possible score from exam paper questions"""
    max_score = 0
    if not exam_paper:
        return 0
        
    for subject_paper in exam_paper:
        for mcq in subject_paper.get("MCQs", []):
            max_score += get_question_score(mcq, "mcq")
        
        for coding in subject_paper.get("Coding", []):
            max_score += get_question_score(coding, "coding")
        
        for query in subject_paper.get("Query", []):
            max_score += get_question_score(query, "query")
    
    return max_score

def calculate_max_score_from_subjects(subjects: List[Dict]) -> int:
    """Calculate maximum possible score from subject configuration"""
    max_score = 0
    if not subjects:
        return 0
        
    for subject in subjects:
        if not subject:
            continue
            
        mcq_counts = subject.get("selectedMCQs", {}) or {}
        max_score += sum(mcq_counts.values()) if isinstance(mcq_counts, dict) else 0
        
        coding_counts = subject.get("selectedCoding", {}) or {}
        max_score += sum(coding_counts.values()) * DIFFICULTY_SCORES["easy"] if isinstance(coding_counts, dict) else 0
        
        query_counts = subject.get("selectedQuery", {}) or {}
        if isinstance(query_counts, dict):
            easy_queries = query_counts.get("easy", 0) or 0
            medium_queries = query_counts.get("medium", 0) or 0
            hard_queries = query_counts.get("hard", 0) or 0
            max_score += (easy_queries * DIFFICULTY_SCORES["easy"]) + (medium_queries * DIFFICULTY_SCORES["medium"]) + (hard_queries * DIFFICULTY_SCORES["hard"])
    
    return max_score