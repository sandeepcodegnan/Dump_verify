from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import multiple_required
from web.db.db_utils import get_collection

class GetBatchwiseAttendance(Resource):
    def __init__(self):
        super().__init__()
        pass
        
    @multiple_required
    def get(self):
        batch = request.args.get('batch')
        location = request.args.get('location')
        mode = request.args.get('mode')

        if not batch or not location or not mode:
            return {"error": "Missing required fields"}, 400

        # Select collection based on mode is class_attendance, practice_attendance
        if mode == 'class_attendance':
            collection = get_collection('attendance')
        elif mode == 'practice_attendance':
            collection = get_collection('practice_attendance')
        else:
            return {"error": "Invalid mode. Use 'class_attendance' or 'practice_attendance'"}, 400

        attendance = list(collection.find({"$and":[{"batchNo": batch},{"location":location}]}))
        for attend in attendance:
            attend["_id"] = str(attend["_id"])
        return {"message":"Getting All Batchswise Attendance","data": attendance}, 200
    