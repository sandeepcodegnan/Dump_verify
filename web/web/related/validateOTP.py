from flask import request
from pymongo import MongoClient
from flask_restful import Resource
from web.db.db_utils import get_collection, get_db

def get_otp_collection():
    return get_collection('otp')


class ValidateOTP(Resource):
    def __init__(self) -> None:
        super().__init__()
        self.collection = get_otp_collection()
        self.db = get_db()
        
    def post(self):
        data = request.json
        email = data.get("email")
        otp = data.get("otp")

        # Database and collection are handled by db_utils

        user = self.collection.find_one({"email": email})

        if user:
            # Email exists, check password
            if user["otp"] == otp:
                return {"message": "Email validation successful", "student_email":user["email"]}, 200
            else:
                return {"message": "OTP incorrect"}, 400
        else:
            return {"message": "User not found"}, 404
