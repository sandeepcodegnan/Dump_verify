from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import skil_required
from web.db.db_utils import get_collection

def get_courses_skills_collection():
    return get_collection('courses_skills')

collection = get_courses_skills_collection()

class Skills(Resource):
    @skil_required
    def get(self):
        stream = request.args.get("stream")
        if not stream:
            return {"error": "stream is required"}, 400
        
        doc = collection.find_one({}, {stream: 1, "_id": 0})

        if doc is None or stream not in doc:
            return {"error": f"No data found for stream '{stream}'"}, 404

        return {stream: doc[stream]}, 200
    																	