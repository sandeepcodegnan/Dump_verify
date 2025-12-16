from flask import request, send_file
from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from web.db.db_utils import get_client, get_db, get_collection
import pandas as pd
from datetime import datetime
import pytz
import io

class DownloadAppliedStudentList(Resource):
    def __init__(self):
        super().__init__()
        self.client = get_client()
        self.db = get_db()
        self.job_collection = get_collection('jobs')
        self.student_collection = get_collection('students')
    
    @bde_required
    def put(self):
        job_id = request.args.get("job_id")
        if not job_id:
            return {"error": "Missing `job_id` parameter."}, 400

        job = self.job_collection.find_one({"id": job_id})
        if not job:
            return {"error": "Job not found with the provided job_id."}, 404
        
        # Check if deadline is still active
        current_time_obj = datetime.now(pytz.timezone('Asia/Kolkata'))
        job_deadline = pytz.timezone('Asia/Kolkata').localize(datetime.strptime(job.get("deadLine"), "%Y-%m-%d %H:%M"))
        
        if current_time_obj > job_deadline:
            return {"message": "Job deadline has already completed..","deadLine": job_deadline.strftime("%Y-%m-%d %H:%M")},302
        
        current_time = current_time_obj.strftime("%Y-%m-%d %H:%M")
        self.job_collection.update_one({"id": job_id}, {"$set": {"deadLine": current_time, "pre_closed": current_time}})
        return {"status":"Job_updated","message": "Deadline updated successfully", "deadLine": current_time},200

    def post(self):
        student_ids = request.json.get("student_ids", [])
        if not student_ids:
            return {"error": "Missing required parameter: student_ids"}, 400

        # Bulk query instead of individual queries
        students = list(self.student_collection.find({"id": {"$in": student_ids}}))
        
        if len(students) != len(student_ids):
            found_ids = {student["id"] for student in students}
            missing_ids = set(student_ids) - found_ids
            return {"error": f"Students not found with ids: {list(missing_ids)}"}, 404

        students_data = []
        for student in students:
            student_info = {
                "StudentID": student.get("studentId"),
                "BatchNo": student.get("BatchNo"),
                "Name": student.get("name"),
                "Email": student.get("email"),
                "Phone": student.get("studentPhNumber"),
                "Age": student.get("age"),
                "State": student.get("state"),
                "Qualification": student.get("qualification"),
                "highestGraduationpercentage": student.get("highestGraduationpercentage"),
                "TenthStandard": student.get("tenthStandard"),
                "TwelfthStandard": student.get("twelfthStandard"),
                "studentSkills": student.get("studentSkills"),
                "Department": student.get("department"),
                "College": student.get("collegeName"),
                "Location": student.get("location"),
                "Passout Year": student.get("yearOfPassing"),
                "resume_url": student.get("resume_url")
            }
            students_data.append(student_info)
        
        # Create Excel file with specific column order
        df = pd.DataFrame(students_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Applied_Students')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'download_Applied_students.xlsx'
        )