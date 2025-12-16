from flask import request
from web.jwt.auth_middleware import mentor_required
from flask_restful import Resource
from web.db.db_utils import get_collection

class Attendace(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('student_login_details')
        
    @mentor_required
    def post(self):
        course = request.json.get('subject')
        batchNo = request.json.get('batches')
        location = request.json.get('location')
    
        if not (course and batchNo and location):
            return {"error": "Missing required fields"}, 400
        
        # if course == 'Python':
        alldata = list(self.collection.find({"$and":[{"BatchNo":batchNo},{"location":location},{"placed":{"$ne":True}}]},{"studentId": 1, "name":1,"BatchNo": 1, "email": 1}))
        for data in alldata:
            data["_id"] = str(data["_id"])  
        return {"message": "selected batch data","students_data": alldata}, 200
    