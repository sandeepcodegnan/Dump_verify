from flask import request
from flask_restful import Resource
from web.db.db_utils import get_collection, get_db, get_client
from ..jwt.jwt_utils import JWTManager

class SuperAdmin(Resource):
    def __init__(self):
        super().__init__()
        self.client = get_client()
        self.db = get_db()
        self.collection = get_collection('admin')

    def post(self):
        email = request.json.get("email")
        password = request.json.get("password")
        #print('Admins:---','*'*50,email,password)
       
        if self.db.name not in self.client.list_database_names():
            self.client[self.db.name]

        # data = {"email": email,"password": password}
        # self.collection.insert_one(data)

        user = self.collection.find_one({"email": email})

        if not user:
            return {"message": "User not found"}, 404

        if user['usertype'] == "Admin":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location"), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "Login successful", "user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400

        elif user['usertype'] == "superAdmin":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location", ""), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "SuperAdmin Login successful","user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
            
        elif user['usertype'] == "Python":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location", ""), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "Login successful", "user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
            
        elif user['usertype'] == "Java":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location", ""), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "Login successful", "user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
            
        elif user['usertype'] == "superManager":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location", ""), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "Login successful", "user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
        elif user['usertype'] == "sales":
            if user["password"] == password:
                user_data = {"email": user["email"], "userType": user["usertype"], "location": user.get("location", ""), "id": user.get("id", "")}
                access_token = JWTManager.generate_token(user_data)
                refresh_token = JWTManager.generate_refresh_token(user_data)
                return {"message": "Login successful", "user": {"userType": user['usertype'], "email": user['email']}, "access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
        else:
            return {"message": "User not found"}, 404

