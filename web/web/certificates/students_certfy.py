from flask_restful import Resource
from flask import request
import datetime
from web.db.db_utils import get_collection

student_collection = get_collection('students')
batch_collection = get_collection('batches')

class student_Certificate(Resource):
    def __init__(self):
        super().__init__()

    def get(self):
        stdId = request.args.get("stdId")
        if not stdId:
            return {"message": "studentId is required"}, 400

        student = student_collection.find_one({"studentId": stdId})
        if not student:
            return {"message": "Student not found"}, 404
        
        # Get batch info
        batch_no = student.get("BatchNo")
        batch = batch_collection.find_one({"Batch": batch_no})
        if not batch:
            return {"message": "Batch not found"}, 404
        if not batch.get("Status") != "Completed":
            return {"message": "Batch not completed"}, 400
               
        # Check student balance
        balance = student.get("balance")
        if float(balance) != 0:
            return {"message": "Student has pending balance"}, 400
        
        print_dat = datetime.now().strftime("%d %B %Y").title()
        branch_location = student.get("location")
        name = student.get("name")
        batch_name = batch.get("Batch")
        
        
        return {"message": "Student eligible for certificate"}

