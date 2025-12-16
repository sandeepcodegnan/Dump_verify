import pymongo
from flask import request
from web.jwt.auth_middleware import StudentResource,student_required
from flask_restful import Resource
from web.db.db_utils import get_collection
from dateutil import parser
import datetime
import pytz

class StudentEligibleJobs(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('jobs')
        self.student_collection = get_collection('students')
        self.batch_collection = get_collection('batches')
    
    @student_required
    def get(self):
        std_id = request.args.get('studentId')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Search functionality
        search = request.args.get('search')

        student = self.student_collection.find_one({'id': std_id},
        {"BatchNo":1,"email": 1,"name": 1,"id": 1,"highestGraduationpercentage": 1,"studentSkills": 1,"department": 1,"yearOfPassing": 1,"placementStatus":1,"placed":1})
        if not student:
            return {"message": "Student not found"}, 404
        # 2. Load all jobs
        job_cursor = self.collection.find()
        job_list = []
        ist = pytz.timezone('Asia/Kolkata')

        batch_no = student.get("BatchNo", "")
        if batch_no.startswith("DROPOUTS-"):
            return {"message": "You are DROPOUT Student!","status":"DROPOUT"}, 200
        
        # Only check placementStatus if it exists and is explicitly False
        if student.get("placementStatus") == False:
            return {"message":"You have registered without placement support!","status":"not_eligible"},200
        
        # Check if the student is placed
        if student.get("placed") == True:
            return {"message": "You are already placed!","status":"placed"}, 200
        
        # Get batch start date
        batch_start_date = None
        if batch_no:
            batch_info = self.batch_collection.find_one({"Batch": batch_no})
            if batch_info and batch_info.get("StartDate"):
                try:
                    batch_start_date = datetime.datetime.strptime(batch_info["StartDate"], '%Y-%m-%d').date()
                    #print(f"Batch start date found: {batch_start_date}")
                except (ValueError, TypeError):
                    batch_start_date = None
            else:
                print(f"No batch info found for BatchNo: {batch_no}")
        
        #YMD
        threshold_date = datetime.date(2025, 7, 12)
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        for job in job_cursor:
            ts_str = job.get("timestamp")
            deadline = job.get("deadLine")
            if not ts_str:
                continue
            # Parse the job's timestamp
            try:
                job_ts = parser.parse(ts_str)
            except (ValueError, TypeError):
                continue
            job_date = job_ts.date()

            # Build the job dict (common fields)
            deadline_clean = deadline.replace('T', ' ') if deadline else deadline
            if current_timestamp > deadline_clean:
                isActive = False
            else:
                isActive = True
            job_dict = {
                "job_id": job.get("id"),
                "companyName": job.get("companyName"),
                "jobRole": job.get("jobRole"),
                "technologies": job.get("jobSkills"),
                "deadline": job.get("deadLine"),
                "jobLocation": job.get("jobLocation"),
                "isActive": isActive
            }

            # Check batch start date condition for all jobs
            if batch_start_date and job_date < batch_start_date:
                continue
            
            # Skills check (common for both before and after threshold)
            job_skills = set(s.lower() for s in job.get("jobSkills", []))
            student_skills = set(s.lower() for s in student.get("studentSkills", []))
            skills_match = bool(job_skills & student_skills)
            
            # 3a. If the job was posted on or before threshold date, only check skills
            if job_date <= threshold_date:
                if skills_match:
                    job_list.append(job_dict)
                continue
            
            # 3b. For jobs after threshold date, apply all conditions
            # Check BatchNo matches job stack
            job_stacks = job.get("stack", [])
            if job_stacks:
                batch_prefix = batch_no.split('-')[0] if '-' in batch_no else batch_no
                if batch_prefix not in job_stacks:
                    continue
            # Percentage
            percentage_ok = student.get("highestGraduationpercentage", 0) >= float(job.get("percentage", 0))
            # Graduation year
            allowed_years = set(str(y) for y in job.get("graduates", []))
            year_ok = str(student.get("yearOfPassing")) in allowed_years

            # Department/branch
            branch_ok = False
            stu_dept_lower = student.get("department", "").lower()
            job_departments = job.get("department", [])
            if any(dept and dept.lower() == "any branch" for dept in job_departments):
                branch_ok = True  # Accept all students regardless of department
            else:
                for dept_entry in job_departments:
                    if not dept_entry:
                        continue
                    if stu_dept_lower == dept_entry.lower():
                        branch_ok = True
                        break
            if percentage_ok and skills_match and year_ok and branch_ok:
                job_list.append(job_dict)
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            filtered_jobs = []
            for job in job_list:
                # Search in companyName, jobRole, jobSkills, and jobLocation
                company_match = search_lower in job.get("companyName", "").lower()
                role_match = search_lower in job.get("jobRole", "").lower()
                skills_match = any(search_lower in skill.lower() for skill in job.get("technologies", []))
                location_match = search_lower in job.get("jobLocation", "").lower()
                
                if company_match or role_match or skills_match or location_match:
                    filtered_jobs.append(job)
            job_list = filtered_jobs
        
        job_list.reverse()
        
        # Pagination
        total_jobs = len(job_list)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_jobs = job_list[start_idx:end_idx]
        
        return {
            "jobs": paginated_jobs,
            "pagination": {
                "current_page": page,
                "total_pages": (total_jobs + limit - 1) // limit,
                "total_jobs": total_jobs,
                "jobs_per_page": limit
            }
        }, 200
        
    
    """@student_required
    def post(self): #post to get only particular job based on jobId
        jobId = request.json.get('jobId')
        studentId = request.json.get('studentId')
        if not jobId and studentId:
            return {"message": "Missing required fields jobId/studentId"}, 400
        
        student = self.student_collection.find_one({'id': studentId})
        if not student:
            return {"message": "Student not found"}, 404
        
        balance = student.get("balance", "0")
        if float(balance.replace(",", "")) > 0:
            return {"status":"balance_pending","message":f"Please pay the remaining balance of {balance} to access this job."},200

        job = self.collection.find_one({'id': jobId})
        if not job:
            return {"message": "Job not found"}, 404
                
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        deadline = job.get("deadLine")
        deadline_clean = deadline.replace('T', ' ') if deadline else deadline
        
        if current_timestamp > deadline_clean:
            isActive = False
        else:
            isActive = True
        
        job_dict = {
            "job_id": job.get("id"),
            "companyName": job.get("companyName"),
            "jobRole": job.get("jobRole"),
            "graduates": job.get("graduates"),
            "salary": job.get("salary"),
            "educationQualification": job.get("educationQualification"),
            "department": job.get("department"),
            "percentage": job.get("percentage"),
            "technologies": job.get("jobSkills"),
            "deadline": job.get("deadLine"),
            "bond": job.get("bond"),
            "jobLocation": job.get("jobLocation"),
            "specialNote": job.get("specialNote"),
            "timestamp": job.get("timestamp"),
            "interviewMode": job.get("Mode_of_Interview"),
            "isActive": isActive
        }
        
        return {"job": job_dict}, 200"""