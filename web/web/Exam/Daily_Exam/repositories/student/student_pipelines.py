"""Student Domain Pipelines - Flow-Based Organization (SoC)"""
from typing import List, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT EXAM FLOW PIPELINES
# ═══════════════════════════════════════════════════════════════════════════════

def build_exam_totals_pipeline(exam_id: str) -> List[Dict]:
    """STEP 3: Exam Submission - Build aggregation pipeline for exam totals with subject breakdown"""
    return [
        {"$match": {"examId": exam_id}},
        {"$unwind": "$paper"},
        {"$project": {
            "subject": "$paper.subject",
            "mcq_count": {"$size": {"$ifNull": ["$paper.MCQs", []]}},
            "coding_count": {"$size": {"$ifNull": ["$paper.Coding", []]}},
            "query_count": {"$size": {"$ifNull": ["$paper.Query", []]}},
            "totalExamTime": 1
        }},
        {"$group": {
            "_id": None,
            "total_mcq": {"$sum": "$mcq_count"},
            "total_coding": {"$sum": "$coding_count"},
            "total_query": {"$sum": "$query_count"},
            "total_exam_time": {"$first": "$totalExamTime"},
            "subjects": {"$push": {
                "subject": "$subject",
                "mcq_count": "$mcq_count",
                "coding_count": "$coding_count",
                "query_count": "$query_count"
            }}
        }}
    ]

def build_leaderboard_pipeline(date: str, batch: str, location: str) -> List[Dict]:
    """STEP 4: Results & Reporting - Build aggregation pipeline for leaderboard with student lookup"""
    return [
        {"$match": {"batch": batch, "startDate": date, "location": location}},
        {"$lookup": {
            "from": "student_login_details",
            "localField": "studentId",
            "foreignField": "id",
            "as": "student"
        }},
        {"$unwind": "$student"},
        {"$group": {
            "_id": "$studentId",
            "studentName": {"$first": "$student.name"},
            "batch": {"$first": "$batch"},
            "location": {"$first": "$student.location"},
            "totalScore": {"$sum": {"$ifNull": ["$analysis.totalScore", 0]}},
            "avgTimeTaken": {"$avg": {"$ifNull": ["$analysis.totalTimeTaken", 0]}},
            "examCount": {"$sum": 1},
            "attempted": {"$first": {"$ifNull": ["$attempt-status", False]}},
            "examName": {"$first": "$examName"},
            "studentId": {"$first": "$studentId"},
            "cgStudentId": {"$first": "$student.studentId"}
        }},
        {"$sort": {"totalScore": -1, "avgTimeTaken": 1, "studentName": 1}}
    ]