from flask import request, jsonify
from flask_restful import Resource 
from web.jwt.auth_middleware import bde_required
from web.db.db_utils import get_collection
import datetime
import pytz

class GetJobDetails(Resource):
    def __init__(self):
        super().__init__()
        self.job_collection = get_collection('jobs')

    @bde_required
    def get(self):
        job_id = request.args.get('job_id')
        if not job_id:
            return {"error": "Missing 'job_id' parameter"}, 400

        job_document = self.job_collection.find_one({"id": job_id}, {"_id": 0}) 
        if not job_document:
            return {"error": "Job not found"}, 404
            
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        deadline = job_document.get("deadLine")
        if current_timestamp > deadline:
            isActive = False
        else:
            isActive = True
        
        job_document["isActive"] = isActive

        return job_document, 200
