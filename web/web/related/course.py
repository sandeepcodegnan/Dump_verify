from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import all_location
from web.db.db_utils import get_collection

def get_tech_stack_collection():
    return get_collection('tech_stack')

collection = get_tech_stack_collection()


class Subjects(Resource):
    @all_location
    def get(self):
        location = request.args.get('location')

        if not location:
            return {"error": "Location parameter is required"}, 400
        doc = collection.find_one({"location": location}, {"stacks": 1, "_id": 0})
        
        if not doc:
            return {"error": "Location not found"}, 404
            
        return {"stacks": list(doc.get('stacks').keys())}, 200