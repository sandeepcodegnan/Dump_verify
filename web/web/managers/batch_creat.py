from flask import request,jsonify
from flask_restful import Resource
from web.jwt.auth_middleware import All_required,manager_required
from web.db.db_utils import get_collection
import uuid
from datetime import datetime


class CreateBatch(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('batches')

    @manager_required
    def post(self):
        id = str(uuid.uuid4())
        batchno = request.json.get('BatchId').strip()
        course = request.json.get('TechStack')
        startdate = request.json.get('StartDate')
        enddate = request.json.get('EndDate')
        duration = request.json.get('Duration')
        
        # Determine status based on dates
        today = datetime.now().date()
        start_date_obj = datetime.strptime(startdate, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(enddate, '%Y-%m-%d').date()
        
        if end_date_obj < today:
            status = 'Completed'
        elif start_date_obj <= today:
            status = 'Active'
        else:
            status = 'Upcoming'
            
        location = request.json.get('location')
    
        


        if not (batchno and course and startdate and enddate  and duration and status):
            return {"error": "Missing required fields"}, 400

        if self.collection.find_one({"$and":[{"Batch": batchno},{"location":location}]}):
            return {"error": "This Batch already exists"}, 409

        batchs_data = {
            "id": id,
            "Batch": batchno,
            "Course": course,
            "Duration": duration,
            "location" :location,
            "StartDate":startdate,
            "EndDate":enddate,
            "Status":status}

        result = self.collection.insert_one(batchs_data)
        batchs_data['_id'] = str(result.inserted_id)

        return {"message": "Batch successfully created", "batchs": batchs_data}, 201
    
    def _update_batch_status(self):
        # Auto-update batch statuses based on current date
        today = datetime.now().date()
        all_batches = self.collection.find({})
        
        for batch in all_batches:
            start_date_obj = datetime.strptime(batch['StartDate'], '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(batch['EndDate'], '%Y-%m-%d').date()
            
            if end_date_obj < today:
                new_status = 'Completed'
            elif start_date_obj <= today:
                new_status = 'Active'
            else:
                new_status = 'Upcoming'
                
            if batch.get('Status') != new_status:
                self.collection.update_one(
                    {"id": batch['id']}, 
                    {"$set": {"Status": new_status}}
                )
    @All_required
    def get(self):
        self._update_batch_status()  # Update status before fetching
        location = request.args.get("location", "").strip().lower()

        query = {} if location == "all" else {"location": location}

        projection = {"password": 0}

        cursor = (
            self.collection
            .find(query, projection)
            .sort("Batch", -1)      # 1 = ascending | -1 = descending
        )

        batches = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            batches.append(doc)

        return {"message": "All batches data", "data": batches}, 200


    @manager_required
    def put(self):
        data = request.json
        id = data.get("id")
        if not id:
            return {"error": "data is required to update a record"}, 400

        batch = self.collection.find_one({"id": id})
        if not batch:
            return {"error": "This batch not found"}, 404

        update_fields = {}
        if "StartDate" in data:
            update_fields["StartDate"] = data["StartDate"]
        if "EndDate" in data:
            update_fields["EndDate"] = data["EndDate"]
        if "Duration" in data:
            update_fields["Duration"] = data["Duration"]  
    
        # Auto-determine status if dates are updated
        if "StartDate" in data or "EndDate" in data:
            startdate = data.get("StartDate", batch["StartDate"])
            enddate = data.get("EndDate", batch["EndDate"])
            
            today = datetime.now().date()
            start_date_obj = datetime.strptime(startdate, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(enddate, '%Y-%m-%d').date()
            
            if end_date_obj < today:
                update_fields["Status"] = 'Completed'
            elif start_date_obj <= today:
                update_fields["Status"] = 'Active'
            else:
                update_fields["Status"] = 'Upcoming'
    
        if update_fields:
            self.collection.update_one({"id": id}, {"$set": update_fields})

        updated_mentor = self.collection.find_one({"id": id})
        updated_mentor["_id"] = str(updated_mentor["_id"])

        return {"message": "Mentor updated successfully", "Mentor": updated_mentor}, 200
