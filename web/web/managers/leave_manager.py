from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import exams_required,manager_required
from web.db.db_utils import get_collection

class ManagerLeaveupdated(Resource):
    def __init__(self):
        super().__init__()
        self.leave_collection = get_collection('leave_request')
        self.manager_collection = get_collection('managers')
    @exams_required
    def get(self):
        location = request.args.get('location')
        
        if location == "all":
            leaves = list(self.leave_collection.find({},{"password":0}))
            for res in leaves:
                res["_id"] = str(res["_id"])
            return {"message":"All leaves locations","leaves":leaves},200
        
        else:       
            leaves = list(self.leave_collection.find({"location":location},{"password":0}))
            for res in leaves:
                res["_id"] = str(res["_id"])
        
        return {"message":"All leaves locations","leaves":leaves},200
    
    @manager_required
    def put(self):
        data = request.json
        id = data.get("studentId")
        managerId = data.get("managerId")

        if not id:
            return {"error": "data is required to update a record"}, 400

        manager = self.manager_collection.find_one({"id":managerId})
        if not manager:
            return {"error": "Manager with the specified Id not found"}, 404
        update_fields = {}
        if "status" in data:
            update_fields["status"] = data["status"]
            update_fields["AcceptedBy"]=manager['name']
        
        if update_fields:
            self.leave_collection.update_one({"id": id}, {"$set": update_fields})

        updated = self.leave_collection.find_one({"id": id})
        updated["_id"] = str(updated["_id"])

        

        return {"message": "Manager updated successfully", "manager": updated}, 200
