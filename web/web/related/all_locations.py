from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import all_location
from web.db.db_utils import get_collection

def get_locations_collection():
    return get_collection('locations')

collection = get_locations_collection()

class Locations(Resource):
    @all_location
    def get(self):
        doc = collection.find_one({}, {"_id": 0})      
        if doc is None:
            return {"error": "No data found"}, 404
        
        return doc.get("locations", []), 200

