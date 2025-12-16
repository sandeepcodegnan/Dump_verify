"""
Central utility functions for student search operations
"""
import base64

def normalize_phone_search(search):
    """Normalize phone number for search variations"""
    clean_search = search.replace(" ", "")
    search_variations = [search, clean_search]
    
    if clean_search.isdigit():
        if len(clean_search) == 10:
            search_variations.extend([f"+91{clean_search}", f"91{clean_search}", f"+91 {clean_search}", f"91 {clean_search}"])
        elif len(clean_search) == 12 and clean_search.startswith("91"):
            ten_digit = clean_search[2:]
            search_variations.extend([ten_digit, f"+{clean_search}", f"+91 {ten_digit}", f"91 {ten_digit}"])
    elif clean_search.startswith("+91"):
        if len(clean_search) == 13:
            ten_digit = clean_search[3:]
            twelve_digit = clean_search[1:]
            search_variations.extend([ten_digit, twelve_digit, f"+91 {ten_digit}", f"91 {ten_digit}"])
        elif len(clean_search) == 14:  # "+91 xxxxxxxxxx"
            ten_digit = clean_search[4:]
            search_variations.extend([ten_digit, f"91{ten_digit}", f"+91{ten_digit}", f"91 {ten_digit}"])
    
    return list(set(search_variations))

def build_search_query(search):
    """Build MongoDB search query"""
    search_variations = normalize_phone_search(search)
      
    return {
        "$or": [
            {"studentId": search},
            {"studentPhNumber": {"$in": search_variations}},
            {"parentNumber": {"$in": search_variations}}
        ]
    }

def build_fast_search_query(search):
    """Ultra-fast exact query for indexed fields"""
    clean_search = search.replace(" ", "")
    
    if search.isalnum() and not search.isdigit() and len(search) >= 6:
        return {"studentId": search}
    
    search_variations = normalize_phone_search(search)
    return {
        "$or": [
            {"studentPhNumber": {"$in": search_variations}},
            {"parentNumber": {"$in": search_variations}}
        ]
    }

def build_ultra_fast_query(search):
    """Ultra-fast query - studentId is always alphanumeric, pure numbers are phone numbers"""
    clean_search = search.replace(" ", "")
    
    if search.isalnum() and not search.isdigit() and len(search) >= 3:
        return {"studentId": search}
    
    search_variations = normalize_phone_search(search)
    if search_variations:
        return {
            "$or": [
                {"studentPhNumber": {"$in": search_variations}},
                {"parentNumber": {"$in": search_variations}}
            ]
        }
    
    return None

def find_student(std_collection, search_query):
    """Find student and return formatted data with only used fields"""
    projection = get_optimized_projection()
    student_data = std_collection.find_one(search_query, projection)
    if not student_data:
        return None
    student_data["_id"] = str(student_data["_id"])
    return student_data

def find_student_for_details(std_collection, search_query):
    """Ultra-fast aggregation pipeline for Student_Details"""
    pipeline = [
        {"$match": search_query},
        {
            "$project": {
                "_id": 1,
                "id": 1,
                "name": 1,
                "studentId": 1,
                "BatchNo": 1,
                "email": 1,
                "studentPhNumber": 1,
                "parentNumber": 1,
                "ModeofStudey": 1,
                "location": 1,
                "balance": 1,
                "duedate": 1,
                "invoiceURL": 1,
                "paidamount": 1,
                "total": 1,
                "batchNo": 1,
                "age": 1,
                "collegeName": 1,
                "collegeUSNNumber": 1,
                "department": 1,
                "githubLink": 1,
                "highestGraduationpercentage": 1,
                "qualification": 1,
                "state": 1,
                "studentSkills": 1,
                "yearOfPassing": 1,
                "placed": 1,
                "placementStatus": 1,
                "bloodGroup": 1,
                "resume_url": 1,
                "profile_url": 1
            }
        },
        {"$limit": 1}
    ]
    
    result = list(std_collection.aggregate(pipeline))
    if not result:
        return None
    
    student_data = result[0]
    student_data["_id"] = str(student_data["_id"])
    return student_data

def find_student_by_id_location(std_collection, std_id, location):
    """Find student by ID and location with optimized projection"""
    projection = get_optimized_projection()
    student_data = std_collection.find_one(
        {"studentId": std_id, "location": location},
        projection
    )
    if not student_data:
        return None
    student_data["_id"] = str(student_data["_id"])
    return student_data

def format_applied_jobs(job_collection, applied_jobs):
    """Format applied jobs data"""
    DATE_FIELDS = ['timestamp', 'createdAt', 'updatedAt', 'deadline', 'postedDate']
    
    applied_jobs_data = list(job_collection.find(
        {"id": {"$in": applied_jobs}}
    ).sort("timestamp", -1))
    
    for job in applied_jobs_data:
        job["_id"] = str(job["_id"])
        for field in DATE_FIELDS:
            if field in job and hasattr(job[field], 'isoformat'):
                job[field] = job[field].isoformat()
            elif field in job and job[field]:
                job[field] = str(job[field])
        job["applicants_ids"] = [str(app_id) for app_id in job.get("applicants_ids", [])]
    return applied_jobs_data

def validate_student_status(student_data):
    """Centralized student status validation"""
    # Check DROPOUT status
    batch_no = student_data.get("BatchNo", "")
    if batch_no.startswith("DROPOUTS-"):
        return {"message": "You are DROPOUT Student!", "status": "DROPOUT"}, 200
    
    # Check placement status - treat placementStatus == False same as placed students
    if student_data.get("placementStatus") == False:
        return "PLACED_STUDENT", None  # Special flag for placement restricted students
    
    # Check if already placed - return special flag for placed students
    if student_data.get("placed") == True:
        return "PLACED_STUDENT", None  # Special flag for placed students
    
    return None  # No validation issues

def get_section_data(section, student_data, std_id, self_instance, request, is_placed=False):
    """Get data for specific section"""
    from web.student.search_student.profile_service import profile_service
    from web.student.search_student.attendance_service import Attendance_service
    from web.student.search_student.eligiable_job_services import Eligiable_jobs
    from web.student.search_student.exam_service import get_exam_results_optimized
    
    # If student is placed and requesting non-Student_Details, return placed message
    if is_placed and section != 'Student_Details':
        return {"message": "You are already placed!"}
    
    section_handlers = {
        'Student_Details': lambda: handle_fast_student_details(student_data, self_instance, std_id),
        'Applied_Jobs': lambda: handle_applied_jobs(student_data, self_instance.job_collection),
        'Eligible_Jobs': lambda: handle_eligible_jobs(std_id, self_instance),
        'Attendance_Overview': lambda: Attendance_service(self_instance, std_id),
        'Exams_Details': lambda: get_exam_results_optimized(self_instance, student_data, request)
    }
    return section_handlers.get(section, lambda: None)()

def handle_fast_student_details(student_data, self_instance, std_id):
    """Ultra-fast Student_Details handler - returns base64 string like old code"""
    # Check if profile_url exists in student data
    profile_url = student_data.get("profile_url")
    
    if profile_url and "s3.amazonaws.com" in profile_url:
        # Extract S3 key from URL and get data
        try:
            # Extract key from URL: https://bucket.s3.amazonaws.com/key -> key
            s3_key = profile_url.split('.s3.amazonaws.com/')[-1]
            s3_data = self_instance.get_from_s3(s3_key)
            if s3_data:
                return base64.b64encode(s3_data).decode('utf-8')
            return None
        except Exception as e:
            print(f"S3 fetch failed: {e}")
            return None
    else:
        # Fallback to profile service for S3/MongoDB lookup
        from web.student.search_student.profile_service import profile_service
        return profile_service(self_instance, std_id)

def handle_applied_jobs(student_data, job_collection):
    """Optimized applied jobs with aggregation pipeline"""
    from web.db.db_utils import get_collection
    std_collection = get_collection('students')
    student_id = student_data.get("studentId")
    
    # Ultra-fast aggregation to get applied_jobs
    pipeline = [
        {"$match": {"studentId": student_id}},
        {"$project": {"applied_jobs": 1, "_id": 0}},
        {"$limit": 1}
    ]
    
    result = list(std_collection.aggregate(pipeline))
    applied_jobs = result[0].get("applied_jobs", []) if result else []
    
    if not applied_jobs:
        return {"applied_jobs_details": [], "message": "Student found but hasn't applied to any jobs"}
    
    # Optimized job details aggregation
    job_pipeline = [
        {"$match": {"id": {"$in": applied_jobs}}},
        {
            "$project": {
                "_id": 1,
                "id": 1,
                "companyName": 1,
                "jobRole": 1,
                "salary": 1,
                "jobLocation": 1,
                "deadLine": 1,
                "timestamp": 1,
                #"applicants_ids": 1
            }
        },
        {"$sort": {"timestamp": -1}}
    ]
    
    applied_jobs_data = list(job_collection.aggregate(job_pipeline))
    
    # Fast formatting
    for job in applied_jobs_data:
        job["_id"] = str(job["_id"])
        if "timestamp" in job and hasattr(job["timestamp"], 'isoformat'):
            job["timestamp"] = job["timestamp"].isoformat()
        job["applicants_ids"] = [str(app_id) for app_id in job.get("applicants_ids", [])]
    
    return {
        "applied_jobs_details": applied_jobs_data,
        "applied_jobs_count": len(applied_jobs_data)
    }

def handle_eligible_jobs(std_id, self_instance):
    """Handle eligible jobs section"""
    from web.student.search_student.eligiable_job_services import Eligiable_jobs
    eligible_jobs = Eligiable_jobs(self_instance, std_id)
    return {
        "eligible_jobs_details": eligible_jobs,
        "eligible_jobs_count": len(eligible_jobs)
    }

def get_optimized_projection():
    """Get optimized database projection for performance"""
    return {
        "password": 0,
        "ProfileStatus": 0,
        "ArrearsCount": 0,
        "DOB": 0,
        "TenthPassoutYear": 0,
        "TwelfthPassoutYear": 0,
        "arrears": 0,
        "city": 0,
        "gender": 0,
        "tenthStandard": 0,
        "twelfthStandard": 0,
        "timestamp": 0,
        "created_time": 0,
        "applied_jobs": 0,
        "rejected_jobs": 0,
        "selected_jobs": 0,
        "zohoID": 0
    }

def get_student_details_projection():
    """Ultra-fast projection for Student_Details - includes profile_url"""
    return {
        "password": 0,
        "ProfileStatus": 0,
        "ArrearsCount": 0,
        "DOB": 0,
        "TenthPassoutYear": 0,
        "TwelfthPassoutYear": 0,
        "arrears": 0,
        "city": 0,
        "gender": 0,
        "tenthStandard": 0,
        "twelfthStandard": 0,
        "timestamp": 0,
        "created_time": 0,
        "applied_jobs": 0,
        "rejected_jobs": 0,
        "selected_jobs": 0,
        "zohoID": 0
        # profile_url is included for fast profile access
    }

def validate_request_params(search, section, valid_sections):
    """Validate common request parameters"""
    if not search:
        return {"error": "Search parameter is required"}, 400
    
    if section not in valid_sections:
        return {"error": f"Invalid section. Use: {', '.join(valid_sections)}"}, 400
    
    return None

def handle_placed_student_response(section, student_data, std_id, self_instance, request):
    """Handle response for placed students and placementStatus == False students"""
    if section == "Student_Details":
        from web.student.search_student.profile_service import profile_service
        profile = profile_service(self_instance, std_id)
        
        # Determine appropriate message based on student status
        if student_data.get("placed") == True:
            placement = [student_data.get("placed")]
            placement.append("You are already placed!")
            message = "Student found but hasn't applied to any jobs."
        elif student_data.get("placementStatus") == False:
            placement = [False]
            placement.append("You have registered without placement support!")
            message = "Student found but hasn't applied to any jobs."
        else:
            placement = [student_data.get("placed")]
            placement.append("You are already placed!")
            message = "Student found but hasn't applied to any jobs."
            
        return {
            "message": message,
            "placement": placement,
            "student_data": student_data,
            "profile": profile
        }, 200
    else:
        # Return appropriate message for non-Student_Details sections
        if student_data.get("placementStatus") == False:
            return {"message": "You have registered without placement support!"}, 200
        else:
            return {"message": "You are already placed!"}, 200

def build_section_response(section, section_data, student_data):
    """Build response based on section type"""
    response = {"message": "Student found", "student_data": student_data}
    
    if section == "Student_Details":
        response["profile"] = section_data
    elif section == "Applied_Jobs":
        response.update(section_data)
    elif section == "Eligible_Jobs":
        response.update(section_data)
    elif section == "Attendance_Overview":
        response["Attendance"] = section_data
    elif section == "Exams_Details":
        response["Exam_Results"] = section_data
    
    return response