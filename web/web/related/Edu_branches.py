from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import skil_required
from web.db.db_utils import get_collection

def get_educational_branches_collection():
    return get_collection('educational_branches')

collection = get_educational_branches_collection()

class EducationalBranches(Resource):
    @skil_required
    def get(self):
        branch = request.args.get("branch")
        if not branch:
            return {"error": "Branch is required"}, 400
        
        doc = collection.find_one({}, {branch: 1, "_id": 0})

        if doc is None or branch not in doc:
            return {"error": f"No data found for branch '{branch}'"}, 404

        return {branch: doc[branch]}, 200																				