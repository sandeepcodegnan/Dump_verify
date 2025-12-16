from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import all_location
from web.db.db_utils import get_collection

def get_tech_stack_collection():
    return get_collection('tech_stack')

collection = get_tech_stack_collection()

class Designation(Resource):
    @all_location
    def get(self):
        doc = collection.find_one({"designation": {"$exists": True}}, {"designation": 1, "_id": 0})

        if doc is None:
            return {"error": "No data found"}, 404
        
        return doc.get("designation", []), 200

