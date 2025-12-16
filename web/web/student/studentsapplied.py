from flask import request
from web.jwt.auth_middleware import bde_required
from flask_restful import Resource
from web.db.db_utils import get_collection
class    GetAppliedStudentList(Resource):
    def __init__(self):
        super().__init__()
        self.job_collection = get_collection('jobs')
        self.student_collection = get_collection('students')
    
    @bde_required
    def get(self):
        # 1. Validate & parse job_id
        job_id_str = request.args.get("job_id")
        if not job_id_str:
            return {"error": "Missing `job_id` parameter."}, 400

        # If your IDs are numeric in the database, convert here. Otherwise keep as string.
        try:
            job_id = int(job_id_str)
        except ValueError:
            job_id = job_id_str

        # 2. Look up the job document
        job = self.job_collection.find_one({"id": job_id})
        if not job:
            return {"error": "Job not found with the provided job_id."}, 404
        rejected = job.get("rejected_students_ids", [])
        selected = job.get("selected_students_ids", [])
        applicants = job.get("applicants_ids", [])

        # 4. Bulk‐fetch all student docs in one query
        students_cursor = self.student_collection.find({"id": {"$in": applicants}},{"_id": 0})

        # 5. Build the response list
        student_details = []
        for sd in students_cursor:
            student_details.append({
                "id": sd.get("id"),
                "student_id": sd.get("studentId"),
                "BatchNo": sd.get("BatchNo"),
                "name": sd.get("name"),
                "email": sd.get("email"),
                "highestGraduationpercentage": sd.get("highestGraduationpercentage"),
                "studentSkills": sd.get("studentSkills"),
                "phone": sd.get("studentPhNumber"),
                "age": sd.get("age"),
                "state": sd.get("state"),
                "tenthStandard": sd.get("tenthStandard"),
                "twelfthStandard": sd.get("twelfthStandard"),
                "qualification": sd.get("qualification"),
                "yearOfPassing": sd.get("yearOfPassing"),
                "location": sd.get("location"),
                "department": sd.get("department"),
                "collegeName": sd.get("collegeName"),
                "resume_url": sd.get("resume_url"),
            })

        response = {
            "students_applied":      student_details,
            "jobSkills":             job.get("jobSkills", []),
            "rejected_students_ids": rejected,
            "selected_students_ids": selected, }
        return response, 200