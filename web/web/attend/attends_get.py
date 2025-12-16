from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from web.db.db_utils import get_collection
from datetime import datetime

class GetAttendance(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('attendance')
        self.pratice_mentor = get_collection('practice_attendance')

    @mentor_required
    def get(self):
        course = request.args.get('subject')
        batch = request.args.get('batch')
        location = request.args.get('location')
        userType = request.args.get('userType')
        
        if not batch:
            return {"error": "Missing required fields"}, 400 

        # Query based on userType
        if userType == 'Practice_Mentors':
            # Query Practice_Mentors collection
            data = list(self.pratice_mentor.find({"$and":[{"course":course},{"batchNo": batch},{"location":location}]},{"password":0}))
        else:
            # Query Attendance collection (default)
            data = list(self.collection.find({"$and":[{"course":course},{"batchNo": batch},{"location":location}]},{"password":0}))
        
        for item in data:
            item["_id"] = str(item["_id"])
        return {"message":"Getting All Batchwise data","data": data}, 200