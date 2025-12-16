from flask import request
from web.jwt.auth_middleware import admin_required
from flask_restful import Resource
from web.db.db_utils import get_collection, get_db, get_client
import uuid,bcrypt
from datetime import datetime
import smtplib,os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
class BdeSignup(Resource):
    def __init__(self):
        super().__init__()
        self.client = get_client()
        self.db = get_db()
        self.collection = get_collection('bde')
        self.manager_collection = get_collection('managers')
        self.mentor_collection = get_collection('mentors')
        self.student_collection = get_collection('student_login_details')

    def send_email(self, name, email,password):
        # Email content in HTML format
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Codegnan Placements!</title>
            <style>
                /* Global styles */
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #ffffff;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }}
                .content {{
                    text-align: center;
                }}
                h1, p {{
                    margin-bottom: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #FFA500;
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }}
                .button:hover {{
                    background-color: #FFD700;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h1>Welcome to Codegnan...!</h1>
                    <p>Hello, {name},</p>
                    <p>Congratulations on joining our team as a Business Development Executive!</p>
                    <p>We are excited to have you on board and look forward to working together to achieve great success.</p>
                    <p>Below are your login credentials to access the portal:</p>
                        <p>Username: {email}</p>
                        <p>Password: {password}</p>
                        <p>Portal Link: https://placements.codegnan.com/login</p>
                    <p>Explore our website to learn more about our services and offerings.</p>
                    <a href="https://www.codegnan.com" class="button">Explore Now</a>
                </div>
            </div>
        </body>
        </html>
        """

        sender_email = "placements@codegnan.com"
        recipient_email = email
        subject = "Welcome to Codegnan Placements!"

        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))


        smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) 
        smtp_server.starttls()
        smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))   
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()
    @admin_required
    def post(self):
        id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        name = request.json.get('name')
        email = request.json.get("email").lower()
        phNo = request.json.get("PhNumber")
        location =  request.json.get("location")
        usertype = request.json.get("userType")
        password = 'CG@BDE'
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if self.db.name not in self.client.list_database_names():
            self.client[self.db.name]

        if not (name and email and password):
            return {"error": "Missing required fields"}, 400

        if self.collection.find_one({"email": email}):
            return {"error": "Email already exists"}, 409
        
        if self.manager_collection.find_one({"email":email}):
            return {"message": " This mail Already existed in Manager", "status": "error"},404
        
        if self.mentor_collection.find_one({"email":email}):
            return {"message": " This mail Already existed in Mentor", "status": "error"},404
        
        if self.student_collection.find_one({"email":email}):
            return {"message": " This mail Already existed as a Student", "status": "error"},404
        

        bde_data = {
            "id": id,
            "timestamp": timestamp,
            "name": name,
            "email": email,
            "password": h_pwd,
            "PhNumber": phNo,
            "location" :location,
            "usertype":usertype
        }

        result = self.collection.insert_one(bde_data)
        bde_data['_id'] = str(result.inserted_id)

        self.send_email(name, email,password)
        return {"message": "BDE signup successful"}, 201
    
    @admin_required
    def put(self):
        data = request.json
        id = data.get("id")
        email = data.get('email')

        # if self.collection.find_one({"email": email}):
        #     return {"error": "Email already exists"}, 409
        
        if self.manager_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited in Manager", "status": "error"},404
        
        if self.mentor_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited in Mentor", "status": "error"},404
        
        if self.student_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited as a Student", "status": "error"},404
        
        if not id:
            return {"error": "Email is required to update a record"}, 400

        existing_BDE = self.collection.find_one({"id": id})
        if not existing_BDE:
            return {"error": "BDE with the specified email not found"}, 404

        update_fields = {}
        if "name" in data:
            update_fields["name"] = data["name"]
        if "email" in data:
            update_fields["email"] = data["email"]
        if "PhNumber" in data:
            update_fields["PhNumber"] = data["PhNumber"]
        if "location" in data:
            update_fields["location"] = data["location"]
            
    
        if update_fields:
            self.collection.update_one({"id": id}, {"$set": update_fields})

        updated_BDE = self.collection.find_one({"id": id})
        updated_BDE["_id"] = str(updated_BDE["_id"])

        return {"message": "BDE updated successfully", "BDE": updated_BDE}, 200

    @admin_required
    def delete(self):
        id = request.args.get('id')
        if not id:
            return {"error": "data is required to delete a record"}, 400

        result = self.collection.delete_one({"id": id})

        if result.deleted_count == 0:
            return {"error": "BDE with the specified Id not found"}, 404

        return {"message": "BDE deleted successfully"}, 200

    @admin_required
    def get(self):
        BDES = list(self.collection.find({},{"password":0}))
        for BDE in BDES:
            BDE["_id"] = str(BDE["_id"])
        return {"BDE": BDES}, 200