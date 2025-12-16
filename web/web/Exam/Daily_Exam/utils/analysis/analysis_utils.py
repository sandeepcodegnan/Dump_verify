"""Analysis Utilities - DRY Implementation for Exam Analysis"""
from typing import Dict, List
from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS, SUBJECT_QUESTION_TYPES
from web.Exam.Daily_Exam.utils.analysis.score_utils import get_question_score

def build_question_lookup(exam_paper: List[Dict]) -> Dict[str, tuple]:
    """Build question lookup for faster access - DRY utility"""
    question_lookup = {}
    for paper in exam_paper:
        subject = paper.get("subject")
        for mcq in paper.get("MCQs", []):
            question_lookup[mcq.get("questionId")] = (mcq, "MCQ", subject)
        for coding in paper.get("Coding", []):
            question_lookup[coding.get("questionId")] = (coding, "Coding", subject)
        for query in paper.get("Query", []):
            question_lookup[query.get("questionId")] = (query, "Query", subject)
    return question_lookup

def calculate_subject_scores(paper_subjects: List[Dict], analysis_details: List[Dict], fallback_subjects: List[Dict]) -> Dict:
    """Calculate subject-wise scores - DRY utility"""
    subject_map = {}
    subjects_summary = {}
    
    # Handle None inputs
    paper_subjects = paper_subjects or []
    analysis_details = analysis_details or []
    fallback_subjects = fallback_subjects or []
    
    def init_subject(name):
        if name not in subjects_summary:
            subjects_summary[name] = {
                "max_mcq_marks": 0,
                "obtained_mcq_marks": 0,
                "max_code_marks": 0,
                "obtained_code_marks": 0,
                "max_query_marks": 0,
                "obtained_query_marks": 0
            }
    
    # Process paper (MCQ + coding)
    for subj in paper_subjects:
        if not isinstance(subj, dict):
            continue
        std_name = subj.get("subject", "UnknownSubject")
        init_subject(std_name)
        
        for mcq in subj.get("MCQs", []):
            if not isinstance(mcq, dict):
                continue
            qid = mcq.get("questionId")
            mark = get_question_score(mcq, "mcq")
            subjects_summary[std_name]["max_mcq_marks"] += mark
            subject_map[qid] = {"subject": std_name, "type": "mcq"}
        
        for code in subj.get("Coding", []):
            if not isinstance(code, dict):
                continue
            qid = code.get("questionId")
            mark = get_question_score(code, "coding")
            subjects_summary[std_name]["max_code_marks"] += mark
            subject_map[qid] = {"subject": std_name, "type": "code"}
        
        for query in subj.get("Query", []):
            if not isinstance(query, dict):
                continue
            qid = query.get("questionId")
            mark = get_question_score(query, "query")
            subjects_summary[std_name]["max_query_marks"] += mark
            subject_map[qid] = {"subject": std_name, "type": "query"}
    
    # Process analysis (obtained marks)
    for det in analysis_details:
        if not isinstance(det, dict):
            continue
        qid = det.get("questionId")
        mark = det.get("scoreAwarded", 0)
        if qid in subject_map:
            std_name = subject_map[qid]["subject"]
            q_type = subject_map[qid]["type"]
            if q_type == "mcq":
                key = "obtained_mcq_marks"
            elif q_type == "code":
                key = "obtained_code_marks"
            else:  # query
                key = "obtained_query_marks"
            subjects_summary[std_name][key] += mark
    
    # Fallback if no subjects found
    if not subjects_summary:
        fallback = {
            s.get("subject"): {} 
            for s in fallback_subjects 
            if isinstance(s, dict) and s.get("subject")
        }
        subjects_summary = fallback or {"Unknown": {}}
    
    # Add total marks per subject and overall total
    overall_obtained = 0
    for subject, marks in subjects_summary.items():
        if isinstance(marks, dict):
            # Get allowed question types for this subject
            allowed_types = SUBJECT_QUESTION_TYPES.get(subject.lower(), ["mcq"])
            
            # Remove fields not relevant to this subject
            if "code" not in allowed_types:
                marks.pop("max_code_marks", None)
                marks.pop("obtained_code_marks", None)
            if "query" not in allowed_types:
                marks.pop("max_query_marks", None)
                marks.pop("obtained_query_marks", None)
            
            # Calculate totals only from existing fields
            max_total = marks.get("max_mcq_marks", 0) + marks.get("max_code_marks", 0) + marks.get("max_query_marks", 0)
            obtained_total = marks.get("obtained_mcq_marks", 0) + marks.get("obtained_code_marks", 0) + marks.get("obtained_query_marks", 0)
            marks["max_total_marks"] = max_total
            marks["obtained_total_marks"] = obtained_total
            overall_obtained += obtained_total
    
    # Add overall obtained marks to response
    subjects_summary["_overall_obtained"] = overall_obtained
    
    return subjects_summary

def build_subject_breakdown(totals: Dict, total_exam_time: int) -> Dict:
    """Build subject breakdown structure - DRY utility"""
    
    subject_breakdown = {}
    for subj_data in totals.get("subjects", []):
        subj = subj_data["subject"]
        mcq_count = subj_data["mcq_count"]
        
        # Check if SQL subject for query questions
        is_sql_subject = subj.lower() in SQL_SUBJECTS
        
        if is_sql_subject:
            query_count = subj_data.get("query_count", 0)
            total_qs = mcq_count + query_count
            
            subject_breakdown[subj] = {
                "totalQuestions": total_qs,
                "attempted": 0,
                "unattempted": total_qs,
                "score": 0,
                "totalTime": total_exam_time,
                "mcq": {"total": mcq_count, "attempted": 0, "score": 0},
                "query": {"total": query_count, "attempted": 0, "score": 0}
            }
        else:
            coding_count = subj_data["coding_count"]
            total_qs = mcq_count + coding_count
            
            subject_breakdown[subj] = {
                "totalQuestions": total_qs,
                "attempted": 0,
                "unattempted": total_qs,
                "score": 0,
                "totalTime": total_exam_time,
                "mcq": {"total": mcq_count, "attempted": 0, "score": 0},
                "coding": {"total": coding_count, "attempted": 0, "score": 0}
            }
    return subject_breakdown

def process_mcq_answer(qid: str, answer, qdata: Dict, subject: str) -> Dict:
    """Process MCQ answer - DRY utility"""
    if isinstance(answer, dict):
        selected = answer.get("selectedOption", "")
        time_taken = answer.get("timeTaken", 0)
    else:
        selected, time_taken = answer, 0
    
    correct_ans = qdata.get("Correct_Option")
    question_score = get_question_score(qdata, "mcq")
    
    if str(selected).strip().upper() == str(correct_ans).strip().upper():
        status, awarded = "Correct", question_score
        is_correct = True
    else:
        status, awarded = "Incorrect", 0
        is_correct = False
    
    return {
        "questionId": qid,
        "type": "objective",
        "submitted": selected,
        "correctAnswer": correct_ans,
        "scoreAwarded": awarded,
        "status": status,
        "timeTaken": time_taken,
        "question": qdata.get("Question"),
        "options": qdata.get("Options") or {},
        "subject": subject,
        "isCorrect": is_correct
    }

def process_coding_answer(qid: str, answer: Dict, qdata: Dict, subject: str) -> Dict:
    """Process coding answer - DRY utility"""
    if not isinstance(answer, dict) or "testCaseSummary" not in answer:
        return {
            "questionId": qid,
            "type": "code",
            "error": "Invalid coding question submission format.",
            "timeTaken": answer.get("timeTaken", 0) if isinstance(answer, dict) else 0,
            "subject": subject,
            "scoreAwarded": 0,
            "isCorrect": False
        }
    
    # Use question's Score field first, then difficulty from submission, then question difficulty
    question_score = get_question_score(qdata, "coding")
    
    # Override with submission difficulty only if no Score field in question
    if "Score" not in qdata and "score" not in qdata:
        submission_difficulty = answer.get("difficulty")
        if submission_difficulty:
            from web.Exam.Daily_Exam.config.settings import DIFFICULTY_SCORES, DEFAULT_DIFFICULTY_SCORE
            question_score = DIFFICULTY_SCORES.get(submission_difficulty.lower(), DEFAULT_DIFFICULTY_SCORE)
    
    ts = answer.get("testCaseSummary", {})
    passed = ts.get("passed", 0)
    failed = ts.get("failed", 0)
    total = passed + failed
    time_taken = answer.get("timeTaken", 0)
    
    # Calculate status and score
    if total == 0:
        status, awarded, is_correct = "Not Evaluated", 0, False
    elif passed == total:
        status, awarded, is_correct = "Passed", question_score, True
    elif passed == 0:
        status, awarded, is_correct = "Failed", 0, False
    else:
        status = "Partially Passed"
        awarded = round(question_score * (passed / total), 1)
        is_correct = False
    
    return {
        "questionId": qid,
        "type": "code",
        "submitted": answer,
        "sourceCode": answer.get("sourceCode"),
        "scoreAwarded": awarded,
        "status": status,
        "timeTaken": time_taken,
        "question": qdata.get("Question"),
        "subject": subject,
        "isCorrect": is_correct,
        "testCaseSummary": ts
    }

def process_query_answer(qid: str, answer: Dict, qdata: Dict, subject: str) -> Dict:
    """Process query answer - DRY utility"""
    if not isinstance(answer, dict) or "queryResult" not in answer:
        return {
            "questionId": qid,
            "type": "query",
            "error": "Invalid query question submission format.",
            "timeTaken": answer.get("timeTaken", 0) if isinstance(answer, dict) else 0,
            "subject": subject,
            "scoreAwarded": 0,
            "isCorrect": False
        }
    
    question_score = get_question_score(qdata, "query")
    query_result = answer.get("queryResult", {})
    status = query_result.get("status", "Failed")
    time_taken = answer.get("timeTaken", 0)
    
    # Calculate status and score
    if status == "Passed":
        awarded, is_correct = question_score, True
    else:
        awarded, is_correct = 0, False
    
    return {
        "questionId": qid,
        "type": "query",
        "submitted": answer,
        "query": answer.get("query"),
        "scoreAwarded": awarded,
        "status": status,
        "timeTaken": time_taken,
        "question": qdata.get("Question"),
        "subject": subject,
        "isCorrect": is_correct,
        "queryResult": query_result
    }

