from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from flask import request
from web.db.db_utils import get_collection

job_collection = get_collection('jobs')
students_collection = get_collection('students')


class Selected_Stutents_list(Resource):
    def __init__(self):
        super().__init__()
    @bde_required
    def get(self):
        job_id = request.args.get('job_id')
        if not job_id:
            return {"error": "Missing 'job_id' parameter"}, 400

        job_document = job_collection.find_one({"id": job_id}, {"_id": 0})
        if not job_document:
            return {"error": "Job not found"}, 404

        selected_students_data = job_document.get("selected_students_ids", {})
        selected_student_ids = selected_students_data.get("students", []) if isinstance(selected_students_data, dict) else selected_students_data
        if not selected_student_ids:
            return [], 200
            
        students = list(students_collection.find(
            {"id": {"$in": selected_student_ids}}, 
            {"_id": 0, "id": 1,"studentId":1, "name": 1, "email": 1, "studentPhNumber": 1, "highestGraduationpercentage": 1, "department": 1, "location": 1, "yearOfPassing": 1,"studentSkills":1,"resume_url":1}
        ))
        
        students_data = [{"id": student["id"], "email": student["email"], "student_id": student["studentId"], "name": student["name"], "studentPhNumber": student["studentPhNumber"], "department": student["department"],"highestGraduationpercentage": student["highestGraduationpercentage"], "location": student["location"], "yearOfPassing": student["yearOfPassing"],"studentSkills":student["studentSkills"],"resume_url":student.get("resume_url")} for student in students]
        
        selected_comment = selected_students_data.get("selected_comment") if isinstance(selected_students_data, dict) else None
        rejected_students_data = job_document.get("rejected_students_ids", {})
        rejected_comment = rejected_students_data.get("rejected_comment") if isinstance(rejected_students_data, dict) else None
        
        return {"students": students_data, "selected_comment": selected_comment, "rejected_comment": rejected_comment}, 200

"""def get(self):
        job_id = request.args.get('job_id')
        if not job_id:
            return {"error": "Missing 'job_id' parameter"}, 400

        job = job_collection.find_one({"id": job_id}, {"interview_rounds": 1, "_id": 0})
        return job.get("interview_rounds", {}), 200"""