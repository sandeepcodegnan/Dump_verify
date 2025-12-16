from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from web.db.db_utils import get_collection
from datetime import datetime

class EditJob(Resource):
    def __init__(self):
        super().__init__()
        self.update_job = get_collection('jobs')

    @bde_required
    def post(self):
        data = request.get_json()
        job_id = data.get("job_id")
        update_data = {
            "companyName":data.get('companyName'),
            "jobRole": data.get('jobRole'),
            "salary": data.get('salary'),
            "graduates": data.get('graduates',[]),
            "educationQualification": data.get('educationQualification'),
            "department": data.get('department',[]),
            "percentage": data.get('percentage'),
            "jobSkills": data.get("jobSkills", []),
            "jobLocation": data.get('jobLocation'),
            "specialNote": data.get("specialNote"),
            "deadLine": data.get("deadLine"),
            "bond": data.get('bond'),
            "stack" :data.get('stack'),
            "Mode_of_Interview": data.get('interviewMode'),
            "designation": data.get('designation')
            }

        if not job_id:
            return {"error": "Missing required parameter: job_id"}, 400
        else:
            jobs = self.update_job.find_one({"id":job_id})

            if jobs:
                update_data = {k: v for k, v in update_data.items() if v is not None}
                if update_data:
                    update_data["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.update_job.update_one({"id": job_id},{"$set": update_data})
                return {"message": "Job list Updated successful", "userType":"BDE-User","job_id":job_id}, 200
            else:
                # Log or handle if a file is not found
                return {"message": "job list Not found with job_id","job_id":job_id}, 404
            