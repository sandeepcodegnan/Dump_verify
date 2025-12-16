from typing import Dict, Any
from flask import request
from flask_restful import Resource
from bson import SON
from web.Exam.exam_statistics.daily_report_scheduler import start_scheduler
from web.Exam.exam_statistics.shared.exam_report_service import ExamReportService
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document

class ExamReport(Resource):
    def __init__(self):
        self.service = ExamReportService()
    
    def get(self):
        try:
            params = self.service.validate_and_parse_params(
                request.args.get("date"),
                request.args.get("examType", "Daily-Exam"),
                request.args.get("location")
            )
        except ValueError as e:
            return {"error": str(e)}, 400
        
        repo = self.service.get_repository(params["exam_type"])
        return (self._get_optimized_report(repo, params) 
                if params["exam_type"] in {"Weekly-Exam", "Monthly-Exam"} 
                else self._get_legacy_report(repo, params))
    
    def _get_legacy_report(self, repo, params):
        """Generate report for Daily-Exam (legacy schema)"""
        query = self.service.build_query(params["date_key"], params["location_param"])
        total_allocated, total_attempted = self.service.get_basic_counts(repo, query)
        
        pipeline = [
            {"$match": query},
            {"$addFields": {
                "window_start_seconds": "$windowStartTime",
                "window_end_seconds": "$windowEndTime",
                "exam_duration_minutes": "$totalExamTime"
            }},
            {"$addFields": self.service.get_time_conversion_pipeline()},
            {"$group": {
                "_id": {"loc": "$location", "batch": "$batch"},
                "allocated": {"$sum": 1},
                "attempted": {"$sum": {"$cond": ["$attempt-status", 1, 0]}},
                "non_attempted": {"$sum": {"$cond": [{"$not": "$attempt-status"}, 1, 0]}},
                "exam_name": {"$first": "$examName"},
                "window_info": {"$first": {
                    "start": "$window_start_time",
                    "end": "$window_end_time",
                    "duration": "$exam_duration_minutes"
                }}
            }},
            {"$sort": SON([("_id.loc", 1), ("_id.batch", 1)])},
            {"$group": {
                "_id": "$_id.loc",
                "total_batches": {"$sum": 1},
                "batches": {"$push": {
                    "batch": "$_id.batch",
                    "allocated": "$allocated",
                    "attempted": "$attempted",
                    "non_attempted": "$non_attempted",
                    "exam_name": "$exam_name",
                    "window_start_time": "$window_info.start",
                    "window_end_time": "$window_info.end",
                    "exam_duration": "$window_info.duration"
                }},
                "total_allocated": {"$sum": "$allocated"},
                "total_attempted": {"$sum": "$attempted"},
                "total_not_attempted": {"$sum": "$non_attempted"}
            }},
            {"$sort": {"_id": 1}}
        ]

        locations: Dict[str, Any] = {
            doc["_id"]: {
                "total_batches": doc["total_batches"],
                "total_allocated": doc["total_allocated"],
                "total_attempted": doc["total_attempted"],
                "total_not_attempted": doc["total_not_attempted"],
                "batches": doc["batches"]
            }
            for doc in repo.collection.aggregate(pipeline)
        }

        return sanitize_mongo_document({
            "exam_type": params["exam_type"],
            "report_date": params["date_key"],
            "location_filter": params["location_param"] or "all",
            "total_batches": sum(v["total_batches"] for v in locations.values()),
            "total_allocated_students": total_allocated,
            "total_attempted_students": total_attempted,
            "total_not_attempted_students": total_allocated - total_attempted,
            "locations": locations
        })
    
    def _get_optimized_report(self, repo, params):
        """Generate report for Weekly/Monthly exams (optimized schema)"""
        query = self.service.build_query(params["date_key"], params["location_param"])
        
        pipeline = [
            {"$match": query},
            {"$unwind": "$students"},
            {"$addFields": self.service.get_time_conversion_pipeline()},
            {"$group": {
                "_id": {"loc": "$location", "batch": "$batch"},
                "allocated": {"$sum": 1},
                "attempted": {"$sum": {"$cond": ["$students.attempt-status", 1, 0]}},
                "non_attempted": {"$sum": {"$cond": [{"$not": "$students.attempt-status"}, 1, 0]}},
                "exam_name": {"$first": "$examName"},
                "window_info": {"$first": {
                    "start": "$window_start_time",
                    "end": "$window_end_time",
                    "duration": "$totalExamTime"
                }}
            }},
            {"$sort": SON([("_id.loc", 1), ("_id.batch", 1)])},
            {"$group": {
                "_id": "$_id.loc",
                "total_batches": {"$sum": 1},
                "batches": {"$push": {
                    "batch": "$_id.batch",
                    "allocated": "$allocated",
                    "attempted": "$attempted",
                    "non_attempted": "$non_attempted",
                    "exam_name": "$exam_name",
                    "window_start_time": "$window_info.start",
                    "window_end_time": "$window_info.end",
                    "exam_duration": "$window_info.duration"
                }},
                "total_allocated": {"$sum": "$allocated"},
                "total_attempted": {"$sum": "$attempted"},
                "total_not_attempted": {"$sum": "$non_attempted"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        total_allocated = total_attempted = 0
        locations = {}
        
        for doc in repo.collection.aggregate(pipeline):
            locations[doc["_id"]] = {
                "total_batches": doc["total_batches"],
                "total_allocated": doc["total_allocated"],
                "total_attempted": doc["total_attempted"],
                "total_not_attempted": doc["total_not_attempted"],
                "batches": doc["batches"]
            }
            total_allocated += doc["total_allocated"]
            total_attempted += doc["total_attempted"]
        
        return sanitize_mongo_document({
            "exam_type": params["exam_type"],
            "report_date": params["date_key"],
            "location_filter": params["location_param"] or "all",
            "total_batches": sum(v["total_batches"] for v in locations.values()),
            "total_allocated_students": total_allocated,
            "total_attempted_students": total_attempted,
            "total_not_attempted_students": total_allocated - total_attempted,
            "locations": locations
        })

start_scheduler()