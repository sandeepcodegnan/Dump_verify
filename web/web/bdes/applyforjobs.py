from flask import request
from web.jwt.auth_middleware import StudentResource
from web.db.db_utils import get_collection
import uuid,os
from datetime import datetime
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class JobEmailSender(threading.Thread):
    def __init__(self, student_name, student_email, job_data):
        super().__init__()
        self.student_name = student_name
        self.student_email = student_email
        self.job_data = job_data

    def run(self):
        # Send email to the student
        self.send_email(self.student_name, self.student_email, self.job_data)

    def send_email(self, name, email, job_data):
        # Email content in HTML format
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Job Application Confirmation</title>
            <!-- CSS styles -->
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .content {{
                    text-align: left;
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
                }}
                @keyframes fadeIn {{
                    from {{ opacity: 0; }}
                    to {{ opacity: 1; }}
                }}
                .fade-in {{
                    animation: fadeIn 1s ease-in-out;
                }}
            </style>
        </head>
        <body>
            <div class="container fade-in">
                <h1>New Job Application Confirmation</h1>
                <p>Dear {name},</p>
                <p>Thank you for applying for the position of {job_data['jobRole']} at {job_data['companyName']}.</p>
                <p>Here are the details of the job:</p>
                <p>Location: {job_data['jobLocation']}</p>
                <p>CTC: {job_data['salary']}</p>
                <p>We will review your application and contact you soon.</p>
                <p>Best regards,</p>
                <p>The Placement Team</p>
            </div>
        </body>
        </html>
        """

        # Email configuration
        sender_email = "Placements@codegnan.com"
        recipient_email = email
        subject = "Job Application Confirmation"

        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach HTML content to the email
        msg.attach(MIMEText(html_content, 'html'))

        # Send email using SMTP (for Gmail)
        smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) # Update SMTP server details for Gmail
        smtp_server.starttls()
        smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD')) #'Codegnan@0818'  # Update sender's email and password
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()

class JobApplication(StudentResource):
    def __init__(self):
        super().__init__()
        self.job_collection = get_collection('jobs')
        self.student_collection = get_collection('students')

    def post(self):
        # Extract data from the request
        data = request.get_json()
        student_id = data.get('student_id')
        job_id = data.get('job_id')

        # Check if both student_id and job_id are provided
        if not (student_id and job_id):
            return {"error": "Both student_id and job_id are required"}, 400

        # Search for the student document with the provided student_id
        student_document = self.student_collection.find_one({"id": student_id})

        if student_document:
            # Check if student has resume URL
            resume_url = student_document.get('resume_url')
            if not resume_url:
                return {"error": "Resume is required to apply for this job. Please upload your resume to the portal and try again...!"}, 400

        # Search for the job document with the provided job_id
        job_document = self.job_collection.find_one({"id": job_id})

        if job_document:
            # Check if job deadline has passed
            job_deadline = job_document.get('deadLine')
            if job_deadline:
                current_datetime = datetime.now()
                if isinstance(job_deadline, str):
                    try:
                        # Handle ISO format by replacing 'T' with space
                        formatted_deadline = job_deadline.replace('T', ' ')
                        deadline_datetime = datetime.strptime(formatted_deadline, '%Y-%m-%d %H:%M')
                    except ValueError:
                        deadline_datetime = datetime.strptime(job_deadline, '%Y-%m-%d')
                else:
                    deadline_datetime = job_deadline
                
                if current_datetime > deadline_datetime:
                    return {"error": "Job application deadline has expired"}, 400
            
            # Update the job document to append the student_id to the applicants_ids array
            applicants_ids = job_document.get('applicants_ids', [])
            if student_id not in applicants_ids:
                applicants_ids.append(student_id)
                self.job_collection.update_one({"id": job_id}, {"$set": {"applicants_ids": applicants_ids}})
            else:
                return {"error": "Student already applied to this job"}, 400
        else:
            return {"error": "Job not found with the provided job_id"}, 404

        if student_document:
            # Update the student document to append the job_id to the applied_jobs array
            applied_jobs = student_document.get('applied_jobs', [])
            if job_id not in applied_jobs:
                applied_jobs.append(job_id)
                self.student_collection.update_one({"id": student_id}, {"$set": {"applied_jobs": applied_jobs}})
            else:
                return {"error": "Student already applied to this job"}, 400
        else:
            return {"error": "Student not found with the provided student_id"}, 404

        # Start a thread to send email to the student
        email_sender_thread = JobEmailSender(student_document.get('name'), student_document.get('email'), job_document)
        email_sender_thread.start()

        return {"message": "Student applied to job successfully"}, 200