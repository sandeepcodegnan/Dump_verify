from flask import request
from web.jwt.auth_middleware import ManagerResource,manager_required
from flask_restful import Resource
from web.db.db_utils import get_collection
import uuid,os
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random,bcrypt

class Add_Student(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('students')
        self.bde_collection = get_collection('bde')
        self.manager_collection = get_collection('managers')
        self.mentor_collection = get_collection('mentors')

    def send_email(self,email,batchNo,password):

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
                    text-align: left;
                }}
                h1 {{
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
                    <h1>Welcome to Codegnan Placements!</h1>
                    <p>Hello,</p>
                    <p>We are excited to welcome you to the Codegnan Placements Portal, your gateway to exploring placement opportunities and career growth.</p>
                    <p>You are assigned to batch: {batchNo}.</p>
                    <p>Below are your login credentials to access the portal:</p>
                        <p>Username: {email}</p>
                        <p>Password: {password}</p>
                        <p>Portal Link: https://placements.codegnan.com/login</p>
                    <p>Please log in to the portal at your earliest convenience and update your password for security purposes. The platform provides access to job opportunities, placement schedules, and resources to support your career journey.</p>
                    <p>If you face any issues while logging in or have questions, feel free to reach out to us.</p>
                    <p>We wish you all the best as you take the next step toward a bright future!</p>
                    <a href="https://placements.codegnan.com" class="button">Explore Now</a>
                    <p><b>Best Regards,</b></p>
                    <p>CodegnanDestination Placements Team</p>
                </div>
            </div>
        </body>
        </html>
        """


        sender_email = "placements@codegnan.com"
        recipient_email = email
        subject = "Welcome to Codegnan Placements!"

        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))

        smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) 
        smtp_server.starttls()
        smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))   
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        print("New Student mail Sent...!")
        smtp_server.quit()
        

    @manager_required
    def post(self):
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400

        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]



        time = datetime.now().isoformat()
        results = []
        if "studentId" in data and "batchNo" in data:
            studentId = data.get("studentId")
            batchNo = data.get("batchNo")
            email = data.get("email").lower()
            Studentphno = data.get("studentPhNumber")
            parentNo = data.get("parentNumber")
            location = data.get("location")
            mos = data.get('modeOfStudy')
            status = data.get('profileStatus')
            placement = bool(data.get('placementStatus'))
            name = data.get('name')
            placed = data.get('placed')

            if not all([studentId, batchNo, email, parentNo,location]):
                return {"error": "Missing required fields for student"}, 400

            if self.collection.find_one({"studentId": studentId}):
                return {"error": "studentId already exists"}, 404

            if self.collection.find_one({"email": email}):
                return {"error": "Email already exists"}, 404
            
            if self.manager_collection.find_one({"email": email}):
                return {"error": "Email already existed in Manager"}, 404
        
            if self.bde_collection.find_one({"email":email}):
                return {"message": " This mail Already existed in BDE ", "status": "error"},404
            
            if self.mentor_collection.find_one({"email":email}):
                return {"message": " This mail Already existed Mentor", "status": "error"},404

            password = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
            h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            id = str(uuid.uuid4())

            student_data = {
                    "id": id,
                    "studentId": studentId,
                    "BatchNo": batchNo,
                    "email": email,
                    "password": h_pwd,
                    "studentPhNumber":Studentphno,
                    "parentNumber": parentNo,
                    "ModeofStudey":mos,
                    "location" :location,
                    "ProfileStatus":status,
                    "created_time":time,
                    "placementStatus":placement,
                    "name":name,
                    "placed":placed
                }

            result = self.collection.insert_one(student_data)
            student_data['_id'] = str(result.inserted_id)


            self.send_email(email, batchNo, password)

            return {"message": "Student added successfully", "student": student_data}, 200

        #multiple student records
        elif "excelData" in data:
            excel_data = data.get("excelData")
            if not isinstance(excel_data, list):
                return {"error": "Invalid input format. Expected 'excelData' with a list of student data."}, 400

            for student in excel_data:
                studentId = student.get("studentId")
                batchNo = student.get("batchNo")
                email = student.get("email").lower()
                Studentphno = student.get("studentPhNumber")
                parentNo = student.get("parentNumber")
                location = student.get("location")
                mos = student.get('modeOfStudy')
                status = student.get('profileStatus')
                placement = bool(student.get('placementStatus'))
                name = student.get('name')
                placed = student.get('placed')
                if not all([studentId, batchNo, email,Studentphno,parentNo,location]):
                    results.append({"error": "Missing required fields in student record", "student": student})
                    continue
                
                if self.collection.find_one({"studentId": studentId}):
                    results.append({"error": "studentId already exists"})
                    continue

                if self.collection.find_one({"email": email}):
                    results.append({"error": "Email already exists", "email": email})
                    continue

                if self.manager_collection.find_one({"email": email}):
                    results.append({"error": "Email already exists","status": "error"})
                    continue

                if self.bde_collection.find_one({"email":email}):
                    results.append({"message": " This mail Already existed ", "status": "error"})
                    continue
                
                if self.mentor_collection.find_one({"email":email}):
                    results.append({"message": " This mail Already existed ", "status": "error"})
                    continue
                
                password = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
                h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                id = str(uuid.uuid4())

                student_data = {
                    "id": id,
                    "studentId": studentId,
                    "BatchNo": batchNo,
                    "email": email,
                    "password": h_pwd,
                    "studentPhNumber":Studentphno,
                    "parentNumber": parentNo,
                    "ModeofStudey":mos,
                    "location" :location,
                    "ProfileStatus":status,
                    "created_time":time,
                    "placementStatus":placement,
                    "name":name,
                    "placed":placed
                }
                result = self.collection.insert_one(student_data)
                student_data['_id'] = str(result.inserted_id)

                self.send_email(email, batchNo, password)

                results.append({"message": "Student added successfully", "student": student_data}),200

            return {"message": "Students processed", "results": results}, 200

        else:
            return {"error": "Invalid input format"}, 400

