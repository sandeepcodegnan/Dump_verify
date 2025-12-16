from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import multi_admins_required
from web.db.db_utils import get_collection


class AllAdminsCount(Resource):
    def __init__(self):
        super().__init__()
        self.bde_collection = get_collection('bde')
        self.mentor_collection = get_collection('mentors')
        self.manager_collection = get_collection('managers')

    @multi_admins_required
    def get(self):
        bdes = list(self.bde_collection.find({},{"password":0}))
        for bde in bdes:
            bde["_id"] = str(bde["_id"])

        mentors = list(self.mentor_collection.find({},{"password":0}))
        for mentor in mentors:
            mentor["_id"] = str(mentor["_id"])

        managers = list(self.manager_collection.find({},{"password":0}))
        for manager in managers:
            manager["_id"] = str(manager["_id"])
        
        return {"message":"BDE,Mentor,Manager Data","BDE":bdes,"Mentors":mentors,"Managers":managers},200
