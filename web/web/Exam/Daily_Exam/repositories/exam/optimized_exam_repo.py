"""Optimized Exam Repository - For Weekly/Monthly Exams with New Schema"""
from typing import Dict, List, Optional
from web.Exam.exam_central_db import db
from web.Exam.Daily_Exam.utils.security.security_utils import validate_collection_name

class OptimizedExamRepo:
    def __init__(self, collection_name: str):
        collection_name = validate_collection_name(collection_name)
        self.collection = db[collection_name]
    
    def exists_for_date(self, batch: str, location: str, date: str) -> bool:
        """Check if exam exists for given date, batch, location"""
        return bool(self.collection.find_one({
            "startDate": date,
            "batch": batch,
            "location": location
        }))
    
    def create_optimized_exam(self, exam_document: Dict) -> bool:
        """Create single optimized exam document"""
        try:
            self.collection.insert_one(exam_document)
            return True
        except Exception:
            return False
    
    def find_student_exam_by_id(self, exam_id: str) -> Optional[Dict]:
        """Find student's exam data by examId within nested structure"""
        result = self.collection.find_one(
            {"students.examId": exam_id},
            {"students.$": 1, "examName": 1, "startDate": 1, "totalExamTime": 1, 
             "subjects": 1, "windowStartTime": 1, "windowEndTime": 1, "windowDurationSeconds": 1}
        )
        
        if result and "students" in result and result["students"]:
            student_data = result["students"][0]
            # Merge exam metadata with student data
            return {
                **student_data,
                "examName": result["examName"],
                "startDate": result["startDate"],
                "totalExamTime": result["totalExamTime"],
                "subjects": result["subjects"],
                "windowStartTime": result["windowStartTime"],
                "windowEndTime": result["windowEndTime"],
                "windowDurationSeconds": result["windowDurationSeconds"]
            }
        return None
    
    def update_student_paper_and_status(self, exam_id: str, paper: List[Dict]) -> bool:
        """Update student's paper and start status - only for the specific student"""
        from web.Exam.Daily_Exam.utils.time.timeutils import get_ist_timestamp
        
        # Update only the specific student by examId, regardless of other students' status
        result = self.collection.update_one(
            {
                "students": {
                    "$elemMatch": {
                        "examId": exam_id,
                        "start-status": {"$ne": True}
                    }
                }
            },
            {
                "$set": {
                    "students.$.paper": paper,
                    "students.$.start-status": True,
                    "students.$.startTimestamp": get_ist_timestamp()
                }
            }
        )
        return result.matched_count > 0
    
    def submit_student_exam(self, exam_id: str, analysis: Dict) -> bool:
        """Submit student's exam with analysis - only for the specific student"""
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
        
        result = self.collection.update_one(
            {
                "students": {
                    "$elemMatch": {
                        "examId": exam_id,
                        "attempt-status": {"$ne": True}
                    }
                }
            },
            {
                "$set": {
                    "students.$.analysis": analysis,
                    "students.$.attempt-status": True,
                    "students.$.submitTimestamp": get_ist_timestamp()
                }
            }
        )
        return result.matched_count > 0
    
    def get_next_suffix(self, batch: str, exam_type: str) -> int:
        """Get next exam suffix number"""
        pipeline = [
            {"$match": {"batch": batch, "examName": {"$regex": f"^{exam_type}-"}}},
            {"$project": {
                "num": {
                    "$toInt": {
                        "$arrayElemAt": [
                            {"$split": ["$examName", "-"]}, -1
                        ]
                    }
                }
            }},
            {"$group": {"_id": None, "maxNum": {"$max": "$num"}}},
            {"$project": {"num": "$maxNum"}}
        ]
        
        results = list(self.collection.aggregate(pipeline))
        return (results[0]["num"] if results else 0) + 1
    
    def get_exam_day_list(self, batch: str, location: str) -> Dict:
        """Get list of exam days for batch and location"""
        exams = list(self.collection.find(
            {"batch": batch, "location": location},
            {"examName": 1, "batch": 1}
        ))
        
        if not exams:
            raise ValueError("No exam records found for the given batch and location")
        
        exam_list = [{"examName": exam["examName"], "batch": exam["batch"]} for exam in exams]
        return {"success": True, "exams": exam_list}
    
    def get_student_exams(self, student_id: str, limit: int = None) -> List[Dict]:
        """Get student's exam history from nested structure"""
        pipeline = [
            {"$match": {"students.studentId": student_id}},
            {"$unwind": "$students"},
            {"$match": {"students.studentId": student_id}},
            {
                "$project": {
                    "examId": "$students.examId",
                    "examName": 1,
                    "startDate": 1,
                    "totalExamTime": 1,
                    "attempt-status": "$students.attempt-status",
                    "subjects": 1,
                    "paper": "$students.paper",
                    "windowStartTime": 1,
                    "windowEndTime": 1,
                    "windowDurationSeconds": 1
                }
            },
            {"$sort": {"startDate": -1}}
        ]
        
        if limit:
            pipeline.append({"$limit": limit})
        
        return list(self.collection.aggregate(pipeline))
    
    def get_exam_totals(self, exam_id: str) -> Optional[Dict]:
        """Get exam totals for optimized schema with subject breakdown"""
        pipeline = [
            {"$match": {"students.examId": exam_id}},
            {"$unwind": "$students"},
            {"$match": {"students.examId": exam_id}},
            {"$project": {
                "subjects": 1,
                "totalExamTime": 1
            }},
            {"$unwind": "$subjects"},
            {"$facet": {
                "totals": [
                    {"$group": {
                        "_id": None,
                        "total_mcq": {"$sum": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedMCQs.easy", 0]},
                                {"$ifNull": ["$subjects.selectedMCQs.medium", 0]},
                                {"$ifNull": ["$subjects.selectedMCQs.hard", 0]}
                            ]
                        }},
                        "total_coding": {"$sum": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedCoding.easy", 0]},
                                {"$ifNull": ["$subjects.selectedCoding.medium", 0]},
                                {"$ifNull": ["$subjects.selectedCoding.hard", 0]}
                            ]
                        }},
                        "total_query": {"$sum": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedQuery.easy", 0]},
                                {"$ifNull": ["$subjects.selectedQuery.medium", 0]},
                                {"$ifNull": ["$subjects.selectedQuery.hard", 0]}
                            ]
                        }},
                        "total_exam_time": {"$first": "$totalExamTime"}
                    }}
                ],
                "subjects": [
                    {"$group": {
                        "_id": "$subjects.subject",
                        "mcq_count": {"$first": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedMCQs.easy", 0]},
                                {"$ifNull": ["$subjects.selectedMCQs.medium", 0]},
                                {"$ifNull": ["$subjects.selectedMCQs.hard", 0]}
                            ]
                        }},
                        "coding_count": {"$first": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedCoding.easy", 0]},
                                {"$ifNull": ["$subjects.selectedCoding.medium", 0]},
                                {"$ifNull": ["$subjects.selectedCoding.hard", 0]}
                            ]
                        }},
                        "query_count": {"$first": {
                            "$add": [
                                {"$ifNull": ["$subjects.selectedQuery.easy", 0]},
                                {"$ifNull": ["$subjects.selectedQuery.medium", 0]},
                                {"$ifNull": ["$subjects.selectedQuery.hard", 0]}
                            ]
                        }}
                    }},
                    {"$project": {
                        "subject": "$_id",
                        "mcq_count": 1,
                        "coding_count": 1,
                        "query_count": 1,
                        "_id": 0
                    }}
                ]
            }}
        ]
        
        results = list(self.collection.aggregate(pipeline))
        if results:
            totals = results[0]["totals"][0] if results[0]["totals"] else {}
            subjects = results[0]["subjects"] if results[0]["subjects"] else []
            totals["subjects"] = subjects
            return totals
        return None
    
    def get_leaderboard(self, date: str, batch: str, location: str) -> List[Dict]:
        """Get leaderboard data for optimized schema - includes all students like daily exam"""
        pipeline = [
            {"$match": {"startDate": date, "batch": batch, "location": location}},
            {"$unwind": "$students"},
            {"$lookup": {
                "from": "student_login_details",
                "localField": "students.studentId",
                "foreignField": "id",
                "as": "student"
            }},
            {"$unwind": "$student"},
            {"$project": {
                "examName": 1,
                "studentId": "$students.studentId",
                "studentName": "$student.name",
                "cgStudentId": "$student.studentId",
                "totalScore": {"$ifNull": ["$students.analysis.totalScore", 0]},
                "totalTimeTaken": {"$ifNull": ["$students.analysis.totalTimeTaken", 0]},
                "attempted": {"$cond": [{"$eq": ["$students.attempt-status", True]}, True, False]}
            }},
            {"$group": {
                "_id": "$studentId",
                "studentName": {"$first": "$studentName"},
                "cgStudentId": {"$first": "$cgStudentId"},
                "studentId": {"$first": "$studentId"},
                "totalScore": {"$sum": "$totalScore"},
                "avgTimeTaken": {"$avg": "$totalTimeTaken"},
                "examCount": {"$sum": 1},
                "attempted": {"$first": "$attempted"},
                "examName": {"$first": "$examName"}
            }},
            {"$sort": {"totalScore": -1, "avgTimeTaken": 1, "studentName": 1}}
        ]
        return list(self.collection.aggregate(pipeline))
    
    def get_recent_exam_date(self, batch: str, location: str) -> Dict:
        """Get most recent exam date for batch and location"""
        recent_exam = self.collection.find_one(
            {"batch": batch, "location": location},
            {"startDate": 1, "examName": 1},
            sort=[("startDate", -1)]
        )
        return recent_exam if recent_exam else {}
    
    def get_batch_reports_data(self, match_filter: Dict, search: str = None, attempted: str = None, sort_by: str = None, sort_order: str = "asc"):
        """Get batch reports data with student lookup, search, filters and sorting for optimized schema"""
        pipeline = [
            {"$match": match_filter},
            {"$unwind": "$students"},
            {"$lookup": {
                "from": "student_login_details",
                "localField": "students.studentId",
                "foreignField": "id",
                "as": "student"
            }},
            {"$unwind": {"path": "$student", "preserveNullAndEmptyArrays": True}},
            {"$match": {"student": {"$ne": None}}}
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
                pipeline.append({"$match": {"students.attempt-status": True}})
            elif attempted.lower() == "not_attempted":
                pipeline.append({"$match": {"students.attempt-status": {"$ne": True}}})
        
        # Add projection with score calculation
        pipeline.append({
            "$project": {
                "examName": 1,
                "totalExamTime": 1,
                "startDate": 1,
                "subjects": 1,
                "batch": 1,
                "location": 1,
                "paper": "$students.paper",
                "analysis": "$students.analysis",
                "attempt-status": "$students.attempt-status",
                "student.name": 1,
                "student.studentId": 1,
                "student.id": 1,
                "student.studentPhNumber": 1,
                "totalScore": {"$ifNull": ["$students.analysis.totalScore", 0]}
            }
        })
        
        # Add sorting if provided
        if sort_by == "score":
            sort_direction = 1 if sort_order.lower() == "asc" else -1
            pipeline.append({"$sort": {"totalScore": sort_direction}})
        
        return list(self.collection.aggregate(pipeline))
