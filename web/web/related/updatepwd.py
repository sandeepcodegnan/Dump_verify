from flask import request
from flask_restful import Resource
import bcrypt
from web.db.db_utils import get_collection

collection = get_collection('testers')

class Updatepassword(Resource):
    def __init__(self):
        super().__init__()
        # get_collection already imported
        self.std_collection = get_collection('student_login_details')
        self.bde_collection = get_collection('bde')
        self.manager_collection = get_collection('managers')
        self.mentor_collection = get_collection('mentors')
        self.tester_collection = collection

    def post(self):
        email = request.json.get('email')
        password = request.json.get('password')
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if not email or not password:
            return {"error": "Email or password missing. Try again."}, 400

        collections = {
            "Student": self.std_collection,
            "Mentor": self.mentor_collection,
            "Manager": self.manager_collection,
            "BDE": self.bde_collection,
            "Tester":self.tester_collection
        }

        # Find and update user in the appropriate collection
        for role, collection in collections.items():
            user_data = collection.find_one({"email": email})
            if user_data:
                collection.update_one({"email": email}, {"$set": {"password": h_pwd}})
                return {"message": "Password Updated Successfully..!", "user": role}, 200

        return {"message": "No data found for this email"}, 400

    
