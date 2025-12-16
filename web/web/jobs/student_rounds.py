from flask_restful import Resource
from web.jwt.auth_middleware import student_required
from flask import request
import datetime
import pytz
from web.db.db_utils import get_collection

job_collection = get_collection('jobs')
student_collection = get_collection('students')


class Student_Rounds(Resource):
    def __init__(self):
        super().__init__()
        self.job_collection = job_collection
    
    @student_required
    def get(self):
        studentId = request.args.get('studentId')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        if not studentId:
            return {"error": "Missing 'studentId'"}, 400
            
        # First check student_collection for applied jobs list
        student = student_collection.find_one({"id": studentId})
        if not student:
            return {"error": "Student not found"}, 404

        batch_no = student.get("BatchNo", "")
        if batch_no.startswith("DROPOUTS-"):
            return {"message": "You are DROPOUT Student!","status":"DROPOUT"}, 200
        
        # Only check placementStatus if it exists and is explicitly False
        if student.get("placementStatus") == False:
            return {"message":"You have registered without placement support!","status":"not_eligible"},200
            
        # Check if student is placed
        if student.get("placed", False):
            return {"message": "Student is already placed", "status":"placed"}, 200
            
        applied_job_ids = student.get("applied_jobs", [])
        if not applied_job_ids:
            return {
                "studentId": studentId,
                "total_applied_jobs": 0,
                "jobs": [],
                "pagination": {"page": page, "limit": limit, "total_pages": 0}
            }, 200

        # Get jobs from job_collection based on applied job IDs
        query = {"id": {"$in": applied_job_ids}}
        if search:
            query["$or"] = [
                {"companyName": {"$regex": search, "$options": "i"}},
                {"jobRole": {"$regex": search, "$options": "i"}}
            ]
        
        applied_jobs = list(self.job_collection.find(query).sort("_id", -1))
        
        job_status_list = []
        
        for job in applied_jobs:
            job_id = job.get("id")
            
            # STRICT CHECK: Verify student actually applied to this job
            if job_id not in applied_job_ids:
                continue
            
            # Check BDE selection status
            rejected_students_data = job.get("rejected_students_ids")
            selected_students_data = job.get("selected_students_ids")
            
            # If neither field exists, BDE selection is pending
            if rejected_students_data is None and selected_students_data is None:
                bde_status = "pending"
                rejected_students = []
                selected_students = []
            else:
                # Process rejected students
                if isinstance(rejected_students_data, dict):
                    rejected_students = rejected_students_data.get("students", [])
                else:
                    rejected_students = rejected_students_data or []
                
                # Process selected students
                if isinstance(selected_students_data, dict):
                    selected_students = selected_students_data.get("students", [])
                else:
                    selected_students = selected_students_data or []
                
                # Determine BDE status
                if studentId in rejected_students:
                    bde_status = False
                elif studentId in selected_students:
                    bde_status = True
                else:
                    bde_status = "pending"
            
            # Build rounds data based on the new format
            rounds_data = []
            next_round = None
            
            # Always add "applied" round as selected
            rounds_data.append({"round": "applied", "status": "selected"})
            
            # Add "shortlisted" round based on BDE selection
            if bde_status == "pending":
                rounds_data.append({"round": "shortlisted", "status": "pending"})
                next_round = "shortlisted"
            elif bde_status == False:
                rounds_data.append({"round": "shortlisted", "status": "rejected"})
                next_round = None  # Journey ends
            elif bde_status == True:
                rounds_data.append({"round": "shortlisted", "status": "selected"})
                
                # If shortlisted, check interview rounds
                interview_rounds = job.get("interview_rounds", {})
                
                # Check round_1 as screening
                if "round_1" in interview_rounds:
                    screening_data = interview_rounds["round_1"]
                    if studentId in screening_data.get("selected", []):
                        rounds_data.append({"round": "screening", "status": "selected"})
                        # Check what's next after screening
                        if "round_2" in interview_rounds:
                            # Check if student is already processed in round_2
                            round_2_data = interview_rounds["round_2"]
                            if studentId not in round_2_data.get("selected", []) and studentId not in round_2_data.get("rejected", []):
                                next_round = "round_1"
                            else:
                                next_round = None  # Will be set later in the loop
                        elif "round_final" in interview_rounds:
                            # Check if student is already processed in round_final
                            final_data = interview_rounds["round_final"]
                            if studentId not in final_data.get("selected", []) and studentId not in final_data.get("rejected", []):
                                next_round = "round_final"
                            else:
                                next_round = None
                        else:
                            # No more rounds defined after screening, add round_1 as pending
                            rounds_data.append({"round": "round_1", "status": "pending"})
                            next_round = "round_1"
                    elif studentId in screening_data.get("rejected", []):
                        rounds_data.append({"round": "screening", "status": "rejected"})
                        next_round = None  # Journey ends
                    else:
                        rounds_data.append({"round": "screening", "status": "pending"})
                        next_round = "screening"
                else:
                    # No screening round exists, determine what's next
                    if "round_2" in interview_rounds:
                        next_round = "round_1"
                    elif "round_final" in interview_rounds:
                        next_round = "round_final"
                    else:
                        # No interview rounds exist yet, but student is shortlisted
                        # Add screening as pending and set it as next_round
                        rounds_data.append({"round": "screening", "status": "pending"})
                        next_round = "screening"
                
                # Only continue processing if we're not waiting for screening
                if next_round != "screening":
                    # Check numbered rounds: round_2 becomes round_1, round_3 becomes round_2, etc.
                    round_num = 2
                    display_round = 1
                    while f"round_{round_num}" in interview_rounds:
                        round_data = interview_rounds[f"round_{round_num}"]
                        if studentId in round_data.get("selected", []):
                            rounds_data.append({"round": f"round_{display_round}", "status": "selected"})
                            # Check if there's a next round
                            if f"round_{round_num + 1}" in interview_rounds:
                                # Check if student is already processed in next round
                                next_round_data = interview_rounds[f"round_{round_num + 1}"]
                                if studentId not in next_round_data.get("selected", []) and studentId not in next_round_data.get("rejected", []):
                                    next_round = f"round_{display_round + 1}"
                                else:
                                    next_round = None  # Will be set in next iteration
                            elif "round_final" in interview_rounds:
                                # Check if student is already processed in final round
                                final_data = interview_rounds["round_final"]
                                if studentId not in final_data.get("selected", []) and studentId not in final_data.get("rejected", []):
                                    next_round = "round_final"
                                else:
                                    next_round = None
                            else:
                                # No more rounds defined, add next numbered round as pending
                                next_display_round = display_round + 1
                                rounds_data.append({"round": f"round_{next_display_round}", "status": "pending"})
                                next_round = f"round_{next_display_round}"
                        elif studentId in round_data.get("rejected", []):
                            rounds_data.append({"round": f"round_{display_round}", "status": "rejected"})
                            next_round = None  # Journey ends
                            break
                        else:
                            # Student is pending in this round
                            rounds_data.append({"round": f"round_{display_round}", "status": "pending"})
                            next_round = f"round_{display_round}"
                            break
                        round_num += 1
                        display_round += 1
                    
                    # Check final round
                    if "round_final" in interview_rounds and next_round != f"round_{display_round}":
                        final_data = interview_rounds["round_final"]
                        if studentId in final_data.get("selected", []):
                            rounds_data.append({"round": "round_final", "status": "selected"})
                            next_round = None  # Process complete
                        elif studentId in final_data.get("rejected", []):
                            rounds_data.append({"round": "round_final", "status": "rejected"})
                            next_round = None  # Journey ends
                        else:
                            rounds_data.append({"round": "round_final", "status": "pending"})
                            next_round = "round_final"
            
            job_data = {
                "job_id": job_id,
                "company_name": job.get("companyName"),
                "job_title": job.get("jobRole"),
                "rounds": rounds_data
            }
            
            # Only add next_round if it's not None (process not complete)
            if next_round is not None:
                job_data["next_round"] = next_round
                
            job_status_list.append(job_data)
        
        # Pagination
        total_jobs = len(job_status_list)
        total_pages = (total_jobs + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_jobs = job_status_list[start_idx:end_idx]
        
        return {
            "studentId": studentId,
            "total_applied_jobs": total_jobs,
            "jobs": paginated_jobs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_jobs": total_jobs
            }
        }, 200

    def _get_job_data(self, job, job_id, isActive=None):
        # Check if job is active based on deadline if not provided
        if isActive is None:
            ist = pytz.timezone('Asia/Kolkata')
            current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
            deadline = job.get("deadLine")
            deadline_clean = deadline.replace('T', ' ') if deadline else deadline
            
            if current_timestamp > deadline_clean:
                isActive = False
            else:
                isActive = True
        
        return {
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

    @student_required
    def post(self):

        jobId = request.json.get('job_id')
        studentId = request.json.get('studentId')
        
        if not jobId or not studentId:
            return {"message": "Missing required fields jobId/studentId"}, 400
        
        student = student_collection.find_one({'id': studentId})
        if not student:
            return {"message": "Student not found"}, 404
        
        balance = student.get("balance", "0")
        if float(balance.replace(",", "")) > 0:
            return {"status":"balance_pending","message":f"Please pay the remaining balance of {balance} to access this job."},200

        job = self.job_collection.find_one({'id': jobId})
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
        
        # Create job_dict for potential use in responses
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
            "isActive": isActive
        }
        
        # Check if student applied to this job - if not, return job details for application
        if jobId not in student.get("applied_jobs", []):
            return {"jobs": job_dict}, 200

        # Check if studentId is in job's applicants_ids
        applicants_ids = job.get("applicants_ids", [])
        if studentId not in applicants_ids:
            return {"studentId": studentId, "job_id": jobId, "status": "not_in_applicants","jobs": job_dict}, 200
        
        
        # Check BDE selection status
        rejected_students_data = job.get("rejected_students_ids")
        selected_students_data = job.get("selected_students_ids")
        
        # If neither field exists, BDE selection is pending
        if rejected_students_data is None and selected_students_data is None:
            job_data = self._get_job_data(job, jobId, isActive)
            job_data["rounds"] = [
                {"round": "applied", "status": "selected"},
                {"round": "shortlisted", "status": "pending"}
            ]
            job_data["next_round"] = "shortlisted"
            return {
                "studentId": studentId,
                "total_applied_jobs": 1,
                "jobs": job_data
            }, 200
        
        # Process rejected students
        if isinstance(rejected_students_data, dict):
            rejected_students = rejected_students_data.get("students", [])
        else:
            rejected_students = rejected_students_data or []
        
        # Process selected students
        if isinstance(selected_students_data, dict):
            selected_students = selected_students_data.get("students", [])
        else:
            selected_students = selected_students_data or []
        
        if studentId in rejected_students:
            job_data = self._get_job_data(job, jobId, isActive)
            job_data["rounds"] = [
                {"round": "applied", "status": "selected"},
                {"round": "shortlisted", "status": "rejected"}
            ]
            return {
                "studentId": studentId,
                "total_applied_jobs": 1,
                "jobs": job_data
            }, 200
        
        if studentId not in selected_students:
            job_data = self._get_job_data(job, jobId, isActive)
            job_data["rounds"] = [
                {"round": "applied", "status": "selected"},
                {"round": "shortlisted", "status": "pending"}
            ]
            job_data["next_round"] = "shortlisted"
            return {
                "studentId": studentId,
                "total_applied_jobs": 1,
                "jobs": job_data
            }, 200
        
        shortlisted = True
            
        interview_rounds = job.get("interview_rounds", {})
        student_rounds = []
        
        # Check round_1 as screening
        if "round_1" in interview_rounds:
            round_data = interview_rounds["round_1"]
            selected = round_data.get("selected", [])
            rejected = round_data.get("rejected", [])
            
            if studentId in selected:
                student_rounds.append({"round": "screening", "status": "selected"})
            elif studentId in rejected:
                student_rounds.append({"round": "screening", "status": "rejected"})
        
        # Check numbered rounds starting from round_2
        round_num = 2
        while f"round_{round_num}" in interview_rounds:
            round_data = interview_rounds[f"round_{round_num}"]
            
            # Check if student is in selected or rejected arrays
            selected = round_data.get("selected", [])
            rejected = round_data.get("rejected", [])
            
            if studentId in selected:
                student_rounds.append({"round": f"round_{round_num}", "status": "selected"})
            elif studentId in rejected:
                student_rounds.append({"round": f"round_{round_num}", "status": "rejected"})
                break  # Student journey ends here
            
            round_num += 1
        
        # Check final round
        if "round_final" in interview_rounds:
            final_data = interview_rounds["round_final"]
            selected = final_data.get("selected", [])
            rejected = final_data.get("rejected", [])
            
            if studentId in selected:
                student_rounds.append({"round": "round_final", "status": "selected"})
            elif studentId in rejected:
                student_rounds.append({"round": "round_final", "status": "rejected"})
        
        # Transform student_rounds to match GET method format
        rounds_data = [{"round": "applied", "status": "selected"}]
        next_round = None
        
        if shortlisted:
            rounds_data.append({"round": "shortlisted", "status": "selected"})
            
            # Check if screening exists
            screening_found = False
            last_completed_round = 0
            
            # Check if any round is rejected or round_final is selected - if so, process ends
            any_rejected = any(r["status"] == "rejected" for r in student_rounds)
            final_selected = any(r["round"] == "round_final" and r["status"] == "selected" for r in student_rounds)
            
            # Add rounds from student_rounds with proper formatting
            for round_info in student_rounds:
                if round_info["round"] == "screening":
                    rounds_data.append({"round": "screening", "status": round_info["status"]})
                    screening_found = True
                    if round_info["status"] == "selected" and not final_selected and not any_rejected:
                        # Check if there are more rounds after screening
                        if not any(r["round"].startswith("round_") and r["round"] != "round_final" for r in student_rounds):
                            rounds_data.append({"round": "round_1", "status": "pending"})
                            next_round = "round_1"
                    elif round_info["status"] == "pending":
                        next_round = "screening"
                    elif round_info["status"] == "rejected":
                        next_round = None  # Process ends
                elif round_info["round"].startswith("round_") and round_info["round"] != "round_final":
                    # Convert round_2 to round_1, round_3 to round_2, etc.
                    round_num = int(round_info["round"].split("_")[1]) - 1
                    rounds_data.append({"round": f"round_{round_num}", "status": round_info["status"]})
                    if round_info["status"] == "selected":
                        last_completed_round = round_num
                    elif round_info["status"] == "rejected":
                        next_round = None  # Process ends
                elif round_info["round"] == "round_final":
                    rounds_data.append({"round": "round_final", "status": round_info["status"]})
                    if round_info["status"] == "pending":
                        next_round = "round_final"
                    elif round_info["status"] == "selected":
                        next_round = None  # Process complete
                    elif round_info["status"] == "rejected":
                        next_round = None  # Process ends
            
            # Only add more rounds if no rejection and round_final is not selected
            if not any_rejected and not final_selected:
                # If no screening found but shortlisted, add screening as pending
                if not screening_found:
                    rounds_data.append({"round": "screening", "status": "pending"})
                    next_round = "screening"
                
                # If last completed round exists and no final round, add next round as pending
                if last_completed_round > 0 and not any(r["round"] == "round_final" for r in rounds_data):
                    next_round_num = last_completed_round + 1
                    rounds_data.append({"round": f"round_{next_round_num}", "status": "pending"})
                    next_round = f"round_{next_round_num}"
        
        job_data = self._get_job_data(job, jobId, isActive)
        job_data["rounds"] = rounds_data
        if next_round:
            job_data["next_round"] = next_round
        return {
            "studentId": studentId,
            "total_applied_jobs": 1,
            "jobs": job_data
        }, 200
    