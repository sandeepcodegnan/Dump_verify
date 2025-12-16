from flask import request,jsonify
from flask_jwt_extended import create_access_token
from flask_restful import Resource
from web.jwt.jwt_utils import JWTManager
import bcrypt
from web.jwt.auth_middleware import ProtectedResource
from web.db.db_utils import get_collection

class Logins(Resource):
    def __init__(self) -> None:
        super().__init__()
        self.bde_collection = get_collection('bde')
        self.manager_collection = get_collection('managers')
        self.mentor_collection = get_collection('mentors')
        self.student_collection = get_collection('student_login_details')
        self.tester_collection = get_collection('testers')
        self.practice_mentor = get_collection('practice_mentors')
        self.sales_collection = get_collection('sales')
        
    def post(self):
        try:
            email = request.json.get("email")
            password = request.json.get("password")
            #print('data----',email,password)
            # h_password = bcrypt.checkpw(password.encode('utf-8'), password)
            if not email or not password:
                return {"message": "Email and password are required", "status": "error"},404
            
            for collection in [self.bde_collection, self.manager_collection, self.mentor_collection, self.student_collection, self.tester_collection, self.practice_mentor, self.sales_collection]:
                user = collection.find_one({"email": email})
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
                    usertype = collection.name
                    if usertype == 'student_login_details':
                        profile = user["ProfileStatus"].lower() == "true" if isinstance(user["ProfileStatus"], str) else bool(user["ProfileStatus"])
                        USER = {"id":user["id"],"location":user["location"],"email": user["email"],"profile":profile,"userType": usertype}
                        #print('user------------',USER)
                        access_token = JWTManager.generate_token(USER)
                        refresh_token = JWTManager.generate_refresh_token(USER)
                        return {
                            "message": "Login successful",
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "token_type": "Bearer"},200
                    else:
                        USER = {"id":user["id"],"location":user["location"],"email": user["email"],"userType": usertype}
                        #print('user------------',USER)
                        access_token = JWTManager.generate_token(USER)
                        refresh_token = JWTManager.generate_refresh_token(USER)
                        return {
                            "message": "Login successful",
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "token_type": "Bearer"},200
                    
            return {"message": "Invalid email or password", "status": "error"}, 401

        except Exception as e:
            return {"message": f"An error occurred: {str(e)}", "status": "error"},401
