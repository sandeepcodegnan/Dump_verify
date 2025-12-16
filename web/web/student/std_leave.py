from flask import request
from web.jwt.auth_middleware import student_required
from flask_restful import Resource
from web.db.db_utils import get_collection
import uuid

class StudentLeaveRequest(Resource):
    def __init__(self):
        super().__init__()
        self.leave_collection = get_collection('leave_request')

    @student_required
    def post(self):
        id = str(uuid.uuid4())
        stdId = request.json.get('studentId')
        stdName = request.json.get('studentName')
        stdNo = request.json.get('studentNumber')
        parentNo = request.json.get('parentNumber')
        batch = request.json.get('batchNo')
        start = request.json.get('startDate')
        end =request.json.get('endDate')
        reason = request.json.get('reason')
        days = request.json.get('totalDays')
        location = request.json.get('location')
        status = request.json.get('status')

        if not (stdId and start and location and batch and end) :
            return {"error": "Missing required fields"}, 400
        
        leaves={
            "id":id,
            "studentId":stdId,
            "studentName":stdName,
            "studentPhNumber":stdNo,
            "parentPhNumber":parentNo,
            "batchNo":batch,
            "StartDate":start,
            "EndDate":end,
            "Reason":reason,
            "TotalDays":days,
            "location":location,
            "status":status
        }

        leave = self.leave_collection.insert_one(leaves)
        leaves['_id'] = str(leave.inserted_id)

        return {"message":"leave Request data","leaves":leaves},200
    
    @student_required
    def get(self):
        student = request.args.get('studentId')
        location = request.args.get('location')

        leave_data = list(self.leave_collection.find({"$and":[{"studentId":student},{"location":location}]}))
        for res in leave_data:
            res["_id"] = str(res["_id"])
        
        return {"message":"All leaves data","leaves":leave_data},200