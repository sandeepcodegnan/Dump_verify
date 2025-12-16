"""
Email Service
Centralized email operations with security and error handling
"""
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Dict
from web.Exam.Testing.exceptions.testing_exceptions import ExecutionError

class EmailService:
    """Service for email operations"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL')
    
    def send_welcome_email_async(self, name: str, email: str, password: str, designation: str) -> None:
        """Send welcome email in background thread"""
        threading.Thread(
            target=self._send_welcome_email,
            args=(name, email, password, designation),
            daemon=True
        ).start()
    
    def _send_welcome_email(self, name: str, email: str, password: str, designation: str) -> None:
        """Send welcome email with XSS protection"""
        try:
            # Sanitize inputs to prevent XSS
            safe_name = escape(name)
            safe_email = escape(email)
            safe_password = escape(password)
            safe_designation = escape(designation[0] if isinstance(designation, list) else designation)
            
            html_content = self._build_welcome_email_template(
                safe_name, safe_email, safe_password, safe_designation
            )
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = email
            msg['Subject'] = "Welcome to Codegnan Placements!"
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, email, msg.as_string())
                
        except Exception as e:
            # Log error but don't crash the main operation
            print(f"Email sending failed: {str(e)}")
    
    def _build_welcome_email_template(self, name: str, email: str, password: str, designation: str) -> str:
        """Build welcome email HTML template with sanitized inputs"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <title>Welcome to Codegnan!</title>
            <style>
                body{{font-family:Arial;margin:0;background:#f5f5f5}}
                .container{{max-width:600px;margin:20px auto;padding:20px;
                           background:#fff;border-radius:8px;
                           box-shadow:0 2px 6px rgba(0,0,0,0.1)}}
                .button{{display:inline-block;padding:10px 20px;
                         background:#FFA500;color:#fff;text-decoration:none;
                         border-radius:4px}}
                .button:hover{{background:#FFD700}}
            </style>
        </head>
        <body>
            <div class="container">
                <p>Hi {name},</p>
                <p>Welcome to the Codegnan team as our newest <strong>{designation}</strong> intern!</p>
                <p>We're delighted to have you on board and look forward to working together toward great success.</p>
                <p>Below are your portal login credentials:</p>
                <ul>
                    <li><strong>Portal:</strong> <a href="https://placements.codegnan.com/login">https://placements.codegnan.com/login</a></li>
                    <li><strong>Username:</strong> {email}</li>
                    <li><strong>Password:</strong> {password}</li>
                </ul>
                <p>Once you've logged in, feel free to explore the portal and visit our website to learn more about our services and offerings.</p>
                <p>If you have any questions or need assistance, just let me know!</p>
            </div>
        </body>
        </html>
        """