from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import manager_required
from web.db.db_utils import get_collection
from datetime import datetime, timedelta
import re

class GetMissingAttendance(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('attendance')
        self.student_collection = get_collection('student_login_details')

    def _validate_inputs(self, page_str, limit_str):
        """Validate and convert input parameters safely"""
        try:
            page = int(page_str) if page_str else 1
            limit = int(limit_str) if limit_str else 5
            return max(1, page), max(1, min(100, limit))
        except (ValueError, TypeError):
            return 1, 5

    def _sanitize_string(self, value):
        """Sanitize string inputs to prevent injection"""
        if not value or not isinstance(value, str):
            return None
        # Allow alphanumeric, spaces, hyphens, and underscores only
        sanitized = re.sub(r'[^\w\s-]', '', value.strip())
        return sanitized if len(sanitized) <= 50 else sanitized[:50]

    def _get_past_working_days(self, days_count=3):
        """Get past working days (excluding Sundays) as date strings"""
        current_date = datetime.now()
        past_days = []
        days_back = 1
        while len(past_days) < days_count:
            check_date = current_date - timedelta(days=days_back)
            if check_date.weekday() != 6:
                past_days.append(check_date.strftime('%Y-%m-%d'))
            days_back += 1
        return past_days

    #@manager_required
    def get(self):
        # Validate inputs
        batch = self._sanitize_string(request.args.get('batchNo'))
        location = self._sanitize_string(request.args.get('location'))
        search = self._sanitize_string(request.args.get('search'))
        page, limit = self._validate_inputs(request.args.get('page'), request.args.get('limit'))
        
        if not location:
            return {"error": "Missing required field: location"}, 400

        # Get target date range
        target_dates = self._get_past_working_days(3)
        
        # Build optimized aggregation pipeline
        match_stage = {
            "location": location,
            "datetime": {"$in": target_dates}
        }
        
        if batch:
            match_stage["batchNo"] = batch

        # Single optimized aggregation pipeline
        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$students"},
            
            # Early filtering for missing attendance
            {"$match": {
                "$or": [
                    {"students.status": {"$ne": "present"}},
                    {"students.status": {"$exists": False}}
                ]
            }},
            
            # Group by student and subject to count absences
            {"$group": {
                "_id": {
                    "studentId": "$students.studentId",
                    "course": "$course",
                    "batchNo": "$batchNo"
                },
                "studentName": {"$first": "$students.name"},
                "absent_dates": {"$addToSet": "$datetime"},
                "total_classes": {"$sum": 1}
            }},
            
            # Filter students with at least 2 absences
            {"$match": {"$expr": {"$gte": [{"$size": "$absent_dates"}, 2]}}},
            
            # Lookup student details in single operation
            {"$lookup": {
                "from": "student_login_details",
                "localField": "_id.studentId",
                "foreignField": "studentId",
                "as": "studentDetails"
            }},
            
            # Filter students by batch if specified
            *([{"$match": {"studentDetails.BatchNo": batch}}] if batch else []),
            
            # Filter out students not in correct batch
            {"$match": {"studentDetails": {"$ne": []}}},
            
            # Project final structure
            {"$project": {
                "subject": "$_id.course",
                "batchNo": "$_id.batchNo", 
                "studentId": "$_id.studentId",
                "studentName": 1,
                "studentPhNumber": {"$arrayElemAt": ["$studentDetails.studentPhNumber", 0]},
                "parentNumber": {"$arrayElemAt": ["$studentDetails.parentNumber", 0]},
                "total_present": {"$subtract": [3, {"$size": "$absent_dates"}]},
                "total_absent": {"$size": "$absent_dates"},
                "missing_streaks": {"$reverseArray": {"$setIntersection": [target_dates, "$absent_dates"]}}
            }},
            
            # Apply search filter at database level
            *([{"$match": {
                "$or": [
                    {"studentName": {"$regex": f"^{re.escape(search)}", "$options": "i"}},
                    {"studentId": {"$regex": f"^{re.escape(search)}", "$options": "i"}},
                    {"subject": {"$regex": f"^{re.escape(search)}", "$options": "i"}}
                ]
            }}] if search else []),
            
            # Sort by total_absent descending
            {"$sort": {"total_absent": -1}},
            
            # Add pagination metadata
            {"$facet": {
                "data": [
                    {"$skip": (page - 1) * limit},
                    {"$limit": limit}
                ],
                "totalCount": [{"$count": "count"}]
            }}
        ]
        
        try:
            result = list(self.collection.aggregate(pipeline))
        
            if not result or not result[0]['data']:
                available_batches = self.collection.distinct("batchNo", {"location": location})
                return {
                    "error": f"No attendance records found for location: {location}, batch: {batch}. Available batches: {available_batches}"
                }, 404
            
            data = result[0]['data']
            total_count = result[0]['totalCount'][0]['count'] if result[0]['totalCount'] else 0
            
            return {
                "message": "Students attendance analysis by subjects",
                "data": data,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total_count + limit - 1) // limit,
                    "total_records": total_count,
                    "limit": limit,
                    "page_size": len(data)
                }
            }, 200
            
        except Exception as e:
            return {"error": f"Database query failed: {str(e)}"}, 500
    