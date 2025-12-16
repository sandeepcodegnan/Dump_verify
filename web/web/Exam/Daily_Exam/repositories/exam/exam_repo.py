"""Exam Repository - Data Access Layer (SoC)"""
from typing import Dict, List, Optional
from web.Exam.exam_central_db import db
from web.Exam.Daily_Exam.repositories.student.student_pipelines import build_leaderboard_pipeline, build_exam_totals_pipeline
from web.Exam.Daily_Exam.repositories.exam.exam_pipelines import build_exam_suffix_pipeline, build_batch_reports_pipeline
from web.Exam.Daily_Exam.utils.security.security_utils import validate_object_id, validate_collection_name

class ExamRepo:
    def __init__(self, collection_name: str):
        collection_name = validate_collection_name(collection_name)
        self.collection = db[collection_name]
    
    def find_by_id(self, exam_id: str) -> Optional[Dict]:
        exam_id = validate_object_id(exam_id) if len(exam_id) == 24 else exam_id
        return self.collection.find_one({"examId": exam_id})
    
    def exists_for_date(self, batch: str, location: str, date: str) -> bool:
        return bool(self.collection.find_one({
            "startDate": date,
            "batch": batch,
            "location": location
        }))
    
    def create_bulk(self, exams: List[Dict]) -> int:
        # Validate that all exams use the new window-based format
        for exam in exams:
            if "startTime" in exam and "windowStartTime" not in exam:
                raise ValueError(f"Legacy exam format detected for exam {exam.get('examName', 'Unknown')}. Use window-based format instead.")
        
        result = self.collection.insert_many(exams)
        return len(result.inserted_ids)
    
    def update_paper_and_status(self, exam_id: str, paper: List[Dict]) -> bool:
        from web.Exam.Daily_Exam.utils.time.timeutils import get_ist_timestamp
        
        result = self.collection.update_one(
            {"examId": exam_id, "start-status": {"$ne": True}},
            {"$set": {
                "paper": paper, 
                "start-status": True,
                "startTimestamp": get_ist_timestamp()
            }}
        )
        return result.matched_count > 0
    
    def submit_exam(self, exam_id: str, analysis: Dict) -> bool:
        from web.Exam.Daily_Exam.utils.time.timeutils import get_ist_timestamp
        
        # Ensure float precision is maintained for MongoDB storage
        if "totalScore" in analysis:
            analysis["totalScore"] = float(analysis["totalScore"])
        
        # Ensure subject breakdown scores are floats
        if "subjectBreakdown" in analysis:
            for subject_data in analysis["subjectBreakdown"].values():
                if isinstance(subject_data, dict) and "score" in subject_data:
                    subject_data["score"] = float(subject_data["score"])
                    for q_type in ["mcq", "coding", "query"]:
                        if q_type in subject_data and "score" in subject_data[q_type]:
                            subject_data[q_type]["score"] = float(subject_data[q_type]["score"])
        
        # Ensure detail scores are floats
        if "details" in analysis:
            for detail in analysis["details"]:
                if isinstance(detail, dict) and "scoreAwarded" in detail:
                    detail["scoreAwarded"] = float(detail["scoreAwarded"])
        
        result = self.collection.find_one_and_update(
            {"examId": exam_id, "attempt-status": {"$ne": True}},
            {"$set": {
                "analysis": analysis, 
                "attempt-status": True,
                "submitTimestamp": get_ist_timestamp()
            }}
        )
        return result is not None
    
    def get_leaderboard(self, date: str, batch: str, location: str) -> List[Dict]:
        pipeline = build_leaderboard_pipeline(date, batch, location)
        return list(self.collection.aggregate(pipeline))
    
    def get_recent_exam_date(self, batch: str, location: str) -> Dict:
        """Get most recent exam date for batch and location"""
        recent_exam = self.collection.find_one(
            {"batch": batch, "location": location},
            {"startDate": 1, "examName": 1},
            sort=[("startDate", -1)]
        )
        return recent_exam if recent_exam else {}
    
    def get_exam_totals(self, exam_id: str) -> Optional[Dict]:
        pipeline = build_exam_totals_pipeline(exam_id)
        results = list(self.collection.aggregate(pipeline))
        return results[0] if results else None
    
    def get_next_suffix(self, batch: str, exam_type: str) -> int:
        pipeline = build_exam_suffix_pipeline(batch, exam_type)
        results = list(self.collection.aggregate(pipeline))
        return (results[0]["num"] if results else 0) + 1
    
    def get_student_exams(self, student_id: str, limit: int = None) -> List[Dict]:
        query = {"studentId": student_id}
        projection = {
            "examId": 1, "examName": 1, "startDate": 1,
            "totalExamTime": 1, "attempt-status": 1, "subjects": 1, "paper": 1,
            "windowStartTime": 1, "windowEndTime": 1, "windowDurationSeconds": 1
        }
        cursor = self.collection.find(query, projection).sort("startDate", -1)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    def get_exam_day_list(self, batch: str, location: str) -> Dict:
        exams = list(self.collection.find(
            {"batch": batch, "location": location},
            {"examName": 1, "batch": 1}
        ))
        
        if not exams:
            raise ValueError("No exam records found for the given batch and location")
        
        # Remove duplicate exam names
        unique_exam_names = set()
        exam_list = []
        for exam in exams:
            exam_name = exam.get("examName")
            exam_batch = exam.get("batch")
            if exam_name and exam_name not in unique_exam_names:
                unique_exam_names.add(exam_name)
                exam_list.append({"examName": exam_name, "batch": exam_batch})
        
        return {"success": True, "exams": exam_list}
    
    def get_mentor_exam_list(self, batch: str, subjects: List[str] = None) -> Dict:
        query = {"batch": batch}
        if subjects:
            query["subjects.subject"] = {"$in": subjects}
        
        cursor = self.collection.find(query, {"_id": 0, "examName": 1})
        names = {doc["examName"] for doc in cursor}
        
        if not names:
            raise ValueError("No exams found for that batch/subjects")
        
        try:
            exam_list = sorted(names, key=lambda n: int(n.split("-")[-1]), reverse=True)
        except (ValueError, IndexError):
            exam_list = sorted(names, reverse=True)
        
        return {"batch": batch, "examNames": exam_list}
    

    def get_batch_reports_data(self, match_filter: Dict, search: str = None, attempted: str = None, sort_by: str = None, sort_order: str = "asc"):
        """Get batch reports data with student lookup, search, filters and sorting"""
        pipeline = build_batch_reports_pipeline(match_filter, search, attempted, sort_by, sort_order)
        return list(self.collection.aggregate(pipeline))
    
    def update_with_timing(self, exam_id: str, timing_data: Dict) -> bool:
        """Atomic update with student timing data"""
        result = self.collection.update_one(
            {"examId": exam_id, "start-status": {"$ne": True}},
            {"$set": timing_data}
        )
        return result.matched_count > 0
    
    def find_active_exams_in_window(self, batch: str, location: str) -> List[Dict]:
        """Find exams currently in their window period"""
        from web.Exam.Daily_Exam.utils.time.timeutils import now_ist, time_to_seconds
        
        now = now_ist()
        current_seconds = time_to_seconds(now.time())
        
        return list(self.collection.find({
            "batch": batch,
            "location": location,
            "windowStartTime": {"$lte": current_seconds},
            "windowEndTime": {"$gte": current_seconds},
            "start-status": False
        }))
    
    def is_exam_in_window(self, exam_id: str) -> bool:
        """Check if specific exam is currently in its window period"""
        from web.Exam.Daily_Exam.utils.time.timeutils import now_ist, time_to_seconds
        
        exam = self.find_by_id(exam_id)
        if not exam or not exam.get("windowStartTime") or not exam.get("windowEndTime"):
            return False
        
        now = now_ist()
        current_seconds = time_to_seconds(now.time())
        
        return exam["windowStartTime"] <= current_seconds <= exam["windowEndTime"]