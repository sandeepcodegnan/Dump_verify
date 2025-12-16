"""Exam Domain Pipelines - Exam DB Queries (SoC)"""
from typing import List, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# EXAM MANAGEMENT PIPELINES
# ═══════════════════════════════════════════════════════════════════════════════

def build_exam_suffix_pipeline(batch: str, exam_type: str) -> List[Dict]:
    """Examiner: Build aggregation pipeline for exam suffix calculation"""
    return [
        {"$match": {
            "batch": batch,
            "examName": {"$regex": f"^{exam_type}-"}
        }},
        {"$project": {
            "num": {
                "$convert": {
                    "input": {
                        "$arrayElemAt": [
                            {"$split": ["$examName", "-"]}, -1
                        ]
                    },
                    "to": "int",
                    "onError": 0,
                    "onNull": 0
                }
            }
        }},
        {"$sort": {"num": -1}},
        {"$limit": 1}
    ]

def build_eligible_students_pipeline(batch: str, location: str, exam_type: str, exam_date: str) -> List[Dict]:
    """STEP 1: Exam Preparation - Build aggregation pipeline for finding eligible students (Updated for native date objects)"""
    from web.Exam.Daily_Exam.utils.time.timeutils import parse_date_to_native
    
    # Convert string date to native datetime for matching
    native_date = parse_date_to_native(exam_date)
    
    return [
        {"$match": {"BatchNo": batch, "location": location, "placed": {"$ne": True}}},
        {"$lookup": {
            "from": exam_type,
            "let": {"sid": "$id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$studentId", "$$sid"]},
                            {"$or": [
                                {"$eq": ["$date", native_date]},  # Native datetime match
                                {"$eq": ["$startDate", exam_date]}  # String date fallback
                            ]}
                        ]
                    }
                }}
            ],
            "as": "already"
        }},
        {"$match": {"already": {"$size": 0}}},
        {"$project": {"already": 0}}
    ]

def build_batch_reports_pipeline(match_filter: Dict, search: str = None, attempted: str = None, sort_by: str = None, sort_order: str = "asc") -> List[Dict]:
    """Examiner: Build aggregation pipeline for batch reports with student lookup, search, filters and sorting"""
    pipeline = [
        {"$match": match_filter},
        {"$lookup": {
            "from": "student_login_details",
            "localField": "studentId",
            "foreignField": "id",
            "as": "student"
        }},
        {"$unwind": "$student"}
    ]
    
    # Add search filter if provided
    if search:
        search_conditions = {
            "$or": [
                {"student.name": {"$regex": search, "$options": "i"}},
                {"student.studentId": {"$regex": search, "$options": "i"}},
                {"student.studentPhNumber": {"$regex": search, "$options": "i"}}
            ]
        }
        pipeline.append({"$match": search_conditions})
    
    # Add attempted filter if provided
    if attempted:
        if attempted.lower() == "attempted":
            pipeline.append({"$match": {"attempt-status": True}})
        elif attempted.lower() == "not_attempted":
            pipeline.append({"$match": {"attempt-status": {"$ne": True}}})
    
    # Add projection with score calculation
    pipeline.append({
        "$project": {
            "examName": 1,
            "totalExamTime": 1,
            "startDate": 1,
            "studentStartTime": 1,
            "studentEndTime": 1,
            "extensionMinutes": 1,
            "attempt-status": 1,
            "paper": 1,
            "analysis": 1,
            "subjects": 1,
            "batch": 1,
            "location": 1,
            "student.name": 1,
            "student.studentId": 1,
            "student.id": 1,
            "student.studentPhNumber": 1,
            "totalScore": {"$ifNull": ["$analysis.totalScore", 0]}
        }
    })
    
    # Add sorting if provided
    if sort_by == "score":
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        pipeline.append({"$sort": {"totalScore": sort_direction}})
    
    return pipeline

def build_curriculum_pipeline(batch: str, location: str, req_date: str) -> List[Dict]:
    """Simplified curriculum pipeline for better performance"""
    return [
        {"$match": {"batch": batch, "location": location}},
        {"$project": {"curriculumTable": 1}},
        {"$project": {"rows": {"$objectToArray": "$curriculumTable"}}},
        {"$unwind": "$rows"},
        {"$replaceRoot": {"newRoot": "$rows.v"}},
        {"$addFields": {"dateStr": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": "$createdAt"}}}}},
        {"$match": {"dateStr": req_date}},
        {"$unwind": {"path": "$SubTopics", "preserveNullAndEmptyArrays": True}},
        {"$match": {"$or": [{"SubTopics": None}, {"SubTopics.status": "true"}]}},
        {"$group": {
            "_id": "$subject",
            "topics": {"$addToSet": "$Topics"},
            "subtitles": {"$addToSet": "$SubTopics.title"},
            "tags": {"$addToSet": "$SubTopics.tag"}
        }},
        {"$project": {
            "_id": 0,
            "subject": "$_id",
            "topics": {"$filter": {"input": "$topics", "as": "t", "cond": {"$ne": ["$$t", ""]}}},
            "subtitles": {"$filter": {"input": "$subtitles", "as": "s", "cond": {"$ne": ["$$s", ""]}}},
            "tags": {"$filter": {"input": "$tags", "as": "g", "cond": {"$ne": ["$$g", ""]}}}
        }}
    ]

def build_curriculum_range_pipeline(batch: str, location: str, start_date: str, end_date: str) -> List[Dict]:
    """Curriculum pipeline for date range (Weekly-Exam)"""
    return [
        {"$match": {"batch": batch, "location": location}},
        {"$project": {"curriculumTable": 1}},
        {"$project": {"rows": {"$objectToArray": "$curriculumTable"}}},
        {"$unwind": "$rows"},
        {"$replaceRoot": {"newRoot": "$rows.v"}},
        {"$addFields": {"dateStr": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": "$createdAt"}}}}},
        {"$match": {"dateStr": {"$gte": start_date, "$lte": end_date}}},
        {"$unwind": {"path": "$SubTopics", "preserveNullAndEmptyArrays": True}},
        {"$match": {"$or": [{"SubTopics": None}, {"SubTopics.status": "true"}]}},
        {"$group": {
            "_id": "$subject",
            "topics": {"$addToSet": "$Topics"},
            "subtitles": {"$addToSet": "$SubTopics.title"},
            "tags": {"$addToSet": "$SubTopics.tag"}
        }},
        {"$project": {
            "_id": 0,
            "subject": "$_id",
            "topics": {"$filter": {"input": "$topics", "as": "t", "cond": {"$ne": ["$$t", ""]}}},
            "subtitles": {"$filter": {"input": "$subtitles", "as": "s", "cond": {"$ne": ["$$s", ""]}}},
            "tags": {"$filter": {"input": "$tags", "as": "g", "cond": {"$ne": ["$$g", ""]}}}
        }}
    ]

def build_difficulty_breakdown_pipeline(tags: List[str]) -> List[Dict]:
    """Examiner: Build aggregation pipeline for difficulty breakdown"""
    return [
        {"$match": {"Tags": {"$in": tags}}},
        {"$group": {
            "_id": None,
            "easy": {"$sum": {"$cond": [{"$eq": [{"$toLower": "$Difficulty"}, "easy"]}, 1, 0]}},
            "medium": {"$sum": {"$cond": [{"$eq": [{"$toLower": "$Difficulty"}, "medium"]}, 1, 0]}},
            "hard": {"$sum": {"$cond": [{"$eq": [{"$toLower": "$Difficulty"}, "hard"]}, 1, 0]}}
        }}
    ]

