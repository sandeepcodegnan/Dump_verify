from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import manager_student
from web.db.db_utils import get_collection

def get_tech_stack_collection():
    return get_collection('tech_stack')

collection = get_tech_stack_collection()

class TechStack(Resource):
    @manager_student
    def get(self):
        location = request.args.get('location')

        if not location:
            return {"error": "Location parameter is required"}, 400
        doc = collection.find_one({"location": location}, {"stacks": 1, "_id": 0})

        return {"stacks": doc.get('stacks')}, 200