from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import multiple_required
from web.db.db_utils import get_collection


class GetScheduledData(Resource):
    def __init__(self):
        super().__init__()
        self.schedule_collection = get_collection('schedule')
        self.batches_collection = get_collection('batches')

    @multiple_required
    def get(self):
        location = request.args.get('location')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        # Get completed batch numbers
        completed_batch_numbers = [batch["Batch"] for batch in self.batches_collection.find({"Status": "Completed"}, {"Batch": 1})]
        
        # Build query filter
        query_filter = {
            "batchNo": {"$not": {"$in": completed_batch_numbers}}
        }
        if location and location != 'all':
            query_filter["location"] = location
        if search:
            query_filter["$or"] = [
                {"MentorName": {"$regex": search, "$options": "i"}},
                {"batchNo": {"$regex": search, "$options": "i"}},
                {"subject": {"$regex": search, "$options": "i"}},
                {"UserType": {"$regex": search, "$options": "i"}},
                {"RoomNo": {"$regex": search, "$options": "i"}}
            ]
        
        total_count = self.schedule_collection.count_documents(query_filter)
        schedule_data = list(self.schedule_collection.find(query_filter,{"password": 0}).sort("_id", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string
        for data in schedule_data:
            data["_id"] = str(data["_id"])
        
        return {
            "message": "Getting all scheduled data",
            "schedule_data": schedule_data,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_count": total_count,
                "limit": limit
            }
        }, 200