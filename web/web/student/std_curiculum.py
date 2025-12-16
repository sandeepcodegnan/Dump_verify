from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import StudentResource,student_required
from pymongo import MongoClient
from datetime import datetime
import json,os

from web.db.db_utils import get_collection

student_collection = get_collection('students')
mentor_collection = get_collection('mentor_curriculum_table')

class StudentsCurriculum(Resource):
    def __init__(self):
        super().__init__()
  
    @student_required
    def get(self):
        subject = request.args.get('subject')
        location = request.args.get('location')
        batch = request.args.get('batchNo')
        studentId = request.args.get('studentId')

        if not (subject and location and batch) :
            return {"error": "Missing required fields"}, 400
            
        student = student_collection.find_one({'id': studentId})
        if not student:
            return {"message": "Student not found"}, 404
        
        if student.get("duedate"):
            due_date = datetime.strptime(student["duedate"], "%d/%m/%Y")
            if due_date < datetime.now():
                balance = student.get("balance", "0")
                if float(balance.replace(",", "")) > 0:
                    return {"status":"balance_pending","message":f"Your due date has expired. Please pay the remaining balance of {balance} to access this course."},200
        
        
        curiculum_data = list(mentor_collection.find({"subject": subject, "batch": batch,"location":location}))
        for dat in curiculum_data:
            dat["_id"]=str(dat["_id"])

        return {"message":"Daily classes Curriculum","std_curiculum":curiculum_data},200
    