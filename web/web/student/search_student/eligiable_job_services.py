import datetime
import pytz
from dateutil import parser
from web.db.db_utils import get_collection

def Eligiable_jobs(self,std_id):
    student = get_collection('students').find_one({'studentId': std_id},
            {"BatchNo":1,"email": 1,"name": 1,"studentId": 1,"highestGraduationpercentage": 1,"studentSkills": 1,"department": 1,"yearOfPassing": 1,"placementStatus":1,"placed":1})
    if not student:
        return {"message": "Student not found"}, 404
    # Get batch start date first
    batch_start_date = None
    batch_no = student.get("BatchNo")
    if batch_no:
        batch_info = get_collection('batches').find_one({"Batch": batch_no})
        if batch_info and batch_info.get("StartDate"):
            try:
                batch_start_date = datetime.datetime.strptime(batch_info["StartDate"], '%Y-%m-%d').date()
                #print(f"Batch start date found: {batch_start_date}")
            except (ValueError, TypeError):
                batch_start_date = None
        else:
            print(f"No batch info found for BatchNo: {batch_no}")
    # Query jobs from batch start date onwards
        job_query = {}
        if batch_start_date:
            job_query["timestamp"] = {"$gte": batch_start_date.strftime('%Y-%m-%d')}
        
        job_cursor = get_collection('jobs').find(job_query)
        job_list = []
        ist = pytz.timezone('Asia/Kolkata')
        
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
                "timestamp": ts_str,
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
        job_list.reverse()
              
        return job_list