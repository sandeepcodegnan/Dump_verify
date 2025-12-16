from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from web.db.db_utils import get_collection
from datetime import datetime


class AttendCheck(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('attendance')
        self.pratice_mentor = get_collection('practice_attendance')

    @mentor_required
    def post(self):
        course = request.json.get('subject')
        batch = request.json.get('batch')
        date = request.json.get('date')  
        location = request.json.get('location')
        userType = request.json.get('userType')
        
        if not (course and batch and date):
            return {"error": "Missing required fields"}, 400

        # Select collection based on userType
        target_collection = self.pratice_mentor if userType == 'Practice_Mentors' else self.collection
        
        query = {'course': course, 'batchNo': batch,'datetime': date,'location':location}
        existing_attendance = target_collection.find_one(query)
        if existing_attendance:
            existing_attendance['_id'] = str(existing_attendance['_id'])
            return {'Message': "existed", 'data': existing_attendance}, 200
        else:
            return {'Message': "notexisted"}, 202
