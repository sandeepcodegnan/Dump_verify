from flask import request
from flask_restful import Resource
from web.db.db_utils import get_collection
import uuid
from datetime import datetime
import smtplib,os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random,bcrypt
from web.student.zoho_whatsapp import whatsapp_add
from dotenv import load_dotenv

load_dotenv()
class Add_zoho_Student(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('students')
        self.bde_collection = get_collection('bde')
        self.manager_collection = get_collection('managers')
        self.mentor_collection = get_collection('mentors')
        self.batch = get_collection('batches')

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
                    <h1>Welcome to Codegnan Students Portal!</h1>
                    <p>Hello,</p>
                    <p>We are excited to welcome you to the Codegnan Students Portal, your gateway to exploring placement opportunities and career growth.</p>
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
        subject = "Welcome to Codegnan Placements Portal!"

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
    
    def send_error_email(self,subject, body, to_email="jansaida@codegnan.com"): 
        sender_email = "placements@codegnan.com"
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) 
        server.starttls()
        server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

    def send_batchNo_mail(self,email,batchNo):
        content = f"""<div class="content">
                    <h1>Welcome to Codegnan Students Portal!</h1>
                    <p>Hello,</p>
                    <p>We are excited to welcome you to the Codegnan Students Portal, your gateway to exploring placement opportunities and career growth.</p>
                    <p>Now you’ve been assigned to Batch: {batchNo}.</p>
                    <p>Portal Link: https://placements.codegnan.com/login</p>
                    <p>Please log in to the portal at your earliest convenience and update your password for security purposes. The platform provides access to job opportunities, placement schedules, and resources to support your career journey.</p>
                    <p>If you face any issues while logging in or have questions, feel free to reach out to us.</p>
                    <p>We wish you all the best as you take the next step toward a bright future!</p>
                    <a href="https://placements.codegnan.com" class="button">Explore Now</a>
                    <p><b>Best Regards,</b></p>
                    <p>CodegnanDestination Placements Team</p>
                </div>
                """
        sender_email = "placements@codegnan.com"
        recipient_email = email
        subject = "Batch changed in Portal!"

        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(content, 'html'))

        smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) 
        smtp_server.starttls()
        smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))   
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()
        
    def post(self):
        data = request.json
        print("Zoho---post----",data)
        if not data:
            return {"error": "No data provided"}, 400
        
        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        # Collection already initialized via db_utils

        time = datetime.now().isoformat()
        studentId = data.get("studentId").strip()
        batchNo = data.get("batchNo")
        name = data.get("name")
        email = data.get("email").lower()
        Studentphno = data.get("studentPhNumber")
        parentNo = data.get("parentNumber")
        location = data.get("location").lower()
        mos = data.get('modeOfStudy')
        status = data.get('profileStatus')
        zohoID = data.get('zohoId')
        placement_status_str = data.get('placementStatus', 'false')
        placement = placement_status_str.lower() == 'true' if isinstance(placement_status_str, str) else bool(placement_status_str)
        placed = bool(data.get('placed'))

        if not zohoID:
            subject = "Missing zohoID"
            body = f"{data} for this student data. \n\n missing {zohoID} in post method. Please verify the request."
            self.send_error_email(subject, body)
            return {"error": "Missing required fields for student"}, 400
        
        if Studentphno == parentNo:
            subject = "Student and Parent Phone Number are same"
            body = f"{data} for this student data. \n\n Student and Parent Phone Number are same. Please verify the request."
            self.send_error_email(subject, body)
            return {"error": "Student and Parent Phone Number are same"}, 400
        
        # if self.collection.find_one({"studentId": studentId}):
        #     subject = "StudentId Already Exists Error"
        #     body = f"{data} for this student data. \n\n StudentId: {studentId} already exists in the database. Please verify the request."
        #     self.send_error_email(subject, body)
        #     return {"error": "studentId already exists"}, 404

        if self.collection.find_one({"email": email}):
            subject = "Email Already Exists Error"
            body = f"{data} for this student data. \n\n Email: {email} already exists in the database. Please verify the request."
            self.send_error_email(subject, body)
            return {"error": "Email already exists"}, 404

        password = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        id = str(uuid.uuid4())

        student_data = {
                "id": id,
                "zohoID":zohoID,
                "name":name,
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
                "placed":placed
            }
        # if not batchNo and not self.batch.find_one({"Batch": batchNo}):
        #     subject = "Batch Not Found Error"
        #     body = f"{data} for this student data. \n\n BatchNo: {batchNo} not found in the database."
        #     self.send_error_email(subject, body)
        #     return {"error": "Batch not found"}, 404
            
        result = self.collection.insert_one(student_data)
        student_data['_id'] = str(result.inserted_id)
        #sending whatsappnotification
        if studentId and batchNo:
            whatsapp_add(self,phone=Studentphno,name=name,email=email,batchno=batchNo,username=email,password=password)
            self.send_email(email, batchNo, password)
                    
        return {"message": "Student added successfully", "student": student_data}, 200


    def put(self):
        data = request.json
        print("Zoho---put----", data)
        stdid = data.get("studentId")
        zohoId = data.get("zohoId")

        if not stdid :
            return {"message":"Missing required fields"},404
        
        student = self.collection.find_one({"$or":[{ "studentId": stdid },{ "zohoID":zohoId } ]})
        # self.collection.find_one({"studentId": stdid})
        if not student:
            return {"message": "Student not found"}, 404
        
        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]
        password = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        batchNo =  student.get("BatchNo")
        emails = student.get("email")
        if data.get("email"):
            self.collection.update_one({"$or":[{ "studentId": stdid },{ "zohoID":zohoId }]}, {"$set": {"email": data.get("email").lower(),"password":h_pwd}})
            self.send_email(data.get("email"), batchNo, password)
            return {"message": "Student email successfully changed"}, 200
        
        if data.get("studentId") and data.get("batchNo"):
            # Update database first
            self.collection.update_one(
                {"zohoID":zohoId }, 
                {"$set": {"studentId": data.get("studentId"), "BatchNo": data.get("batchNo")}}
            )
            # Then send notifications
            batchNo = data.get("batchNo")
            name = student.get("name")
            email = student.get("email")
            phone = student.get("studentPhNumber")
            if batchNo.startswith("DROPOUTS-"):
                return {"message": "Student updated successfully"}
            else:
                whatsapp_add(self, phone=phone, name=name, email=email, batchno=batchNo, username=email, password=password)
                self.send_email(email, batchNo, password)
                return {"message": "Student updated successfully with studentId and batchNo"}, 200

        elif data.get("batchNo"):
            batchno = data.get("batchNo")
            self.collection.update_one({"$or":[{ "studentId": stdid },{ "zohoID":zohoId }]}, {"$set": {"batchNo": batchno}})
            self.send_batchNo_mail(emails, batchno)
            return {"message": "Student successfully changed batch"}
        
        else:
            placement_status_str = data.get('placementStatus', 'false')
            placement = placement_status_str.lower() == 'true' if isinstance(placement_status_str, str) else bool(placement_status_str)
            
            updated_data = {
                "zohoID":data.get("zohoId"),
                "name": data.get("name"),
                "studentId": data.get("studentId"),
                "studentPhNumber": data.get("studentPhNumber"),
                "parentNumber": data.get("parentNumber"),
                "location": data.get("location").lower(),
                "modeOfStudy": data.get("modeOfStudy"),
                "placementStatus":placement}
                
            self.collection.update_one({"$or":[{ "studentId": stdid },{ "zohoID":zohoId }]},{"$set": updated_data})

        return {"message": "Student updated successfully", "studentId": stdid}, 200
