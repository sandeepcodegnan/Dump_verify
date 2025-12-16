# studentemailvalidation.py
from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from web.db.db_utils import get_collection

def get_otp_collection():
    return get_collection('otp')


class StudentVerification(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_otp_collection()

    def send_email(self, email, otp):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Codegnan Placements!</title>
        </head>
        <body>
            <h1>Welcome to Codegnan Placements!</h1>
                <p>Email verification for Registration!.Your one time password(OTP):-<b>{ otp }</b></p>
                <p>Congratulations on taking the first step towards a successful career!</p>
                <p>At Codegnan Placements, we are committed to helping you achieve your goals and aspirations. Our team of experts is here to support you every step of the way.</p>
                <p>Explore our website to discover a world of opportunities and resources tailored just for you.</p>
        </body>
        </html>
        """
        #Emial detials
        sender_email = "Placements@codegnan.com"
        recipient_email = email
        subject = "One Time password for Codegnan Placements! Registration"
                
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        smtp_server = smtplib.SMTP('email-smtp.us-east-1.amazonaws.com', 587)
        smtp_server.starttls()
        smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))   # Update with your sender's email and password
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()
        
    def post(self):
        email = request.json.get('email')
        if not email:
            return {"error": "Email is required"}, 400
        if self.collection.find_one({"email": email}):
            self.collection.drop()
        
        otp = random.randint(100000, 999999)
        
        # Save OTP to the database
        otp_data = {"email": email,"otp": otp}
        self.collection.insert_one(otp_data)

        # Send OTP email
        self.send_email(email, otp)

        return {"message": "OTP sent successfully"}, 200
    