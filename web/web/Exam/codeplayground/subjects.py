from web.jwt.auth_middleware import student_required
from flask_restful import Resource
from flask import request, g
from web.Exam.exam_central_db import db, student_collection

class GetFirstSubject(Resource):
    @student_required
    def get(self):
        """Extract course code from batch and return first subject - requires batch and location"""
        try:
            # Both batch and location are required
            batch = request.args.get('batch') or request.args.get('batchNo')
            location = request.args.get('location')
            student_id = request.args.get('student_id')
            
            # Check required parameters
            missing_params = []
            if not batch:
                missing_params.append('batch')
            if not location:
                missing_params.append('location')
            if not student_id:
                missing_params.append('student_id')
            
            if missing_params:
                return {
                    "error": f"Required parameters missing: {', '.join(missing_params)}"
                }, 400
            
            # Check if student is placed
            student = (student_collection.find_one({"id": student_id, "location": location}) or 
                      student_collection.find_one({"_id": student_id, "location": location}) or
                      student_collection.find_one({"student_id": student_id, "location": location}))
            
            if not student:
                return {"error": "Student not found"}, 404
            
            if student.get("placed") == True:
                return {"error": "You are already placed!"}, 403
            
            # Extract course code (e.g., PFS from PFS-888)
            course_code = batch.split('-')[0].upper()
            
            # Find course in database
            course = db["Course-Subjects"].find_one({"courseCode": course_code})
            
            if not course:
                return {"error": f"Course {course_code} not found"}, 404
            
            # Return first subject (index 0)
            first_subject = course["subjects"][0]
            
            return {
                "courseCode": course_code,
                "firstSubject": first_subject,
                "batch": batch,
                "location": location
            }
            
        except Exception as e:
            return {"error": str(e)}, 500
