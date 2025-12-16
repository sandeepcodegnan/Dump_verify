from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import all_mangers_required
from web.db.db_utils import get_collection
from dateutil import parser
import datetime
import pytz


class ListOpenings(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('jobs')
        self.student_collection = get_collection('students')
        self.bde_collection = get_collection('bde')
    
    @all_mangers_required
    def get(self):
        # Collections are already initialized in db_utils

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Search parameters
        search_query = {}
        search = request.args.get('search')
        
        if search:
            search_query['$or'] = [
                {'companyName': {'$regex': search, '$options': 'i'}},
                {'jobRole': {'$regex': search, '$options': 'i'}},
                {'jobSkills': {'$regex': search, '$options': 'i'}},
                {'jobLocation': {'$regex': search, '$options': 'i'}}
            ]

        # Get total count for pagination info
        total_jobs = self.collection.count_documents(search_query)
        
        job_documents = self.collection.find(search_query).sort("_id", -1).skip(skip).limit(limit)
        # Prepare the list of job dictionaries
        job_list = []
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        for job_document in job_documents:

            deadline = job_document.get("deadLine")
            deadline_clean = deadline.replace('T', ' ') if deadline else deadline
            # Compare current timestamp with deadline
            if current_timestamp > deadline_clean:
                isActive = False
            else:
                isActive = True
            
            job_dict = {
                "job_id": job_document.get('id'),
                "companyName": job_document.get('companyName'),
                "jobRole": job_document.get('jobRole'),
                #"graduates": job_document.get('graduates'),
                "salary": job_document.get('salary'),
                #"educationQualification": job_document.get('educationQualification'),
                #"department": job_document.get('department'),
                #"percentage": job_document.get('percentage'),
                "technologies": job_document.get('jobSkills'),
                #"bond": job_document.get('bond'),
                "jobLocation": job_document.get('jobLocation'),
                #"specialNote": job_document.get('specialNote'),
                "deadLine": job_document.get("deadLine"),
                #"stack":job_document.get("stack"),
                "isActive": isActive
            }
            job_list.append(job_dict)
        
        # Pagination metadata
        total_pages = (total_jobs + limit - 1) // limit
        
        return {
            "jobs": job_list,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_jobs": total_jobs,
                "limit": limit}
             }, 200

    @all_mangers_required
    def post(self): #post to get only particular job based on jobId
        jobId = request.json.get('jobId')

        if not jobId:
            return {"message": "Job ID is required"}, 400
        
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
        
        # Convert timestamp to IST
        timestamp = job.get("timestamp")
        ist_timestamp = None
        if timestamp:
            utc_dt = parser.parse(timestamp)
            ist_dt = utc_dt.astimezone(ist)
            ist_timestamp = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get BDE name
        bde_id = job.get("Job_posting_BDE_Id")
        bde_name = None
        if bde_id:
            bde_data = self.bde_collection.find_one({"id": bde_id})
            bde_name = bde_data.get("name") if bde_data else None
        
        job_dict = {
            "job_id": job.get("id"),
            "companyName": job.get("companyName"),
            "jobRole": job.get("jobRole"),
            "graduates": job.get("graduates"),
            "salary": job.get("salary"),
            "educationQualification": job.get("educationQualification"),
            "department": job.get("department"),
            "percentage": job.get("percentage"),
            "bond": job.get("bond"),
            "jobLocation": job.get("jobLocation"),
            "specialNote": job.get("specialNote"),
            "deadLine": job.get("deadLine"),
            "jobSkills": job.get("jobSkills"),
            "designation": job.get("designation"),
            "Mode_of_Interview": job.get("Mode_of_Interview"),
            "stack": job.get("stack"),
            "Posted_date": ist_timestamp,
            "bde_name": bde_name,
            "isActive": isActive
        }
        
        return {"job": job_dict}, 200