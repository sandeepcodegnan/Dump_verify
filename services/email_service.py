"""Email service for sending notifications to interns."""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
    
    def send_intern_credentials(self, intern_email, intern_name, username, password, allocated_subjects):
        """Send login credentials and allocation details to intern."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = intern_email
            msg['Subject'] = "Question Bank Verification System - Login Credentials"
            
            # Email body
            subjects_list = ", ".join([subject.title() for subject in allocated_subjects])
            
            body = f"""
Dear {intern_name},

Welcome to the Question Bank Verification System!

Your account has been created with the following details:

Login Credentials:
- Username: {username}
- Password: {password}

Allocated Subjects:
{subjects_list}

You can now log in and start verifying questions for your assigned subjects.

Please change your password after first login for security.

Best regards,
Codegnan Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False
    
    def send_allocation_update(self, intern_email, intern_name, new_subjects):
        """Send notification about new subject allocation."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = intern_email
            msg['Subject'] = "New Subjects Allocated - Question Bank Verification"
            
            subjects_list = ", ".join([subject.title() for subject in new_subjects])
            
            body = f"""
Dear {intern_name},

New subjects have been allocated to you:

New Subjects:
{subjects_list}

Please log in to the Question Bank Verification System to start working on these subjects.

Best regards,
Codegnan Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False