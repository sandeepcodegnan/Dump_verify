from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from web.db.db_utils import get_collection
from datetime import datetime
import uuid

class AttendData(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('attendance')
        self.pratice_mentor = get_collection('practice_attendance')
    
    @mentor_required
    def post(self):
        course = request.json.get('subject')
        batchNo = request.json.get('batch')
        datetime = request.json.get('datetime')
        students = request.json.get('students')
        location = request.json.get('location')
        userType = request.json.get('userType')
        
        id = str(uuid.uuid4())

        if not (course and batchNo and students):
            return {"error": "Missing required fields"}, 400
        
        # Select collection based on userType
        target_collection = self.pratice_mentor if userType == 'Practice_Mentors' else self.collection
        
        if target_collection.find_one({"batchNo": batchNo, "location": location,'datetime':datetime,'course':course}):
            return {"message": "Students Attendance with this batch and location already exists", "status": "duplicate"}, 409

        Attend_data = {
            "id":id,
            "course":course,
            "batchNo":batchNo,
            "students":students,
            "datetime":datetime,
            "location":location
        }
        result = target_collection.insert_one(Attend_data)
        Attend_data['_id'] = str(result.inserted_id)

        return {"message": "Students Attendance Recived",'Attendance':Attend_data,'status':"existed"}, 200
