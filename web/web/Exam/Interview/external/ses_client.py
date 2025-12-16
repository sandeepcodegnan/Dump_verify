"""Amazon SES Client - External Service Integration"""
import time
import threading
import html
import smtplib
import os
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from web.Exam.exam_central_db import student_collection
from web.Exam.Interview.interview_db import generate_personalized_interview_link


class SESClient:
    """External service client for Amazon SES email notifications"""
    
    def __init__(self):
        # Initialize SMTP configuration from env
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL')
        
        # Configurable rate limiting
        self.max_workers = 5
        self.rate_limit_delay = 1  # 1 second between emails
        
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="SMTP-")
        self._rate_limit_lock = threading.Lock()
        self._last_send_time = 0
    
    def send_interview_notifications(self, interview_data: Dict) -> Dict:
        """Send interview notifications asynchronously - fetches student data from DB"""
        
        def notify_student(student_id: str):
            """Send notification to single student with rate limiting"""
            try:
                # Fetch student data from database
                stu = student_collection.find_one({"id": student_id})
                if not stu:
                    return {"status": "error", "student_id": student_id, "error": "student_not_found"}
                
                if stu.get("placed") == True:
                    return {"status": "skipped", "reason": "placed"}
                
                name = stu.get("name")
                email = stu.get("email")
                phone = stu.get("studentPhNumber", "")
                
                if not (name and email):
                    return {"status": "skipped", "reason": "missing_data"}
                
                # Rate limiting: configurable delay between sends
                with self._rate_limit_lock:
                    current_time = time.time()
                    time_since_last = current_time - self._last_send_time
                    if time_since_last < self.rate_limit_delay:
                        time.sleep(self.rate_limit_delay - time_since_last)
                    self._last_send_time = time.time()
                
                # Prepare email content with student details
                subject = f"Codegnan Weekly Interviews Scheduled - {interview_data['job_title']}"
                html_body = self._build_html_email_body(name, email, phone, interview_data)
                text_body = self._build_text_email_body(name, email, interview_data)
                
                # Send email via SES
                success = self._send_email(email, subject, html_body, text_body)
                return {"status": "sent" if success else "failed", "student_id": student_id}
                
            except Exception as e:
                return {"status": "error", "student_id": student_id, "error": str(e)}
        
        # Get student IDs from interview data
        student_ids = interview_data.get("studentIds", [])
        if not student_ids:
            return {"status": "error", "error": "no_student_ids"}
        
        # Submit all tasks asynchronously - don't wait for completion
        futures = []
        for student_id in student_ids:
            future = self.executor.submit(notify_student, student_id)
            futures.append(future)
        
        # Return immediately like Daily-Exam paper generation
        return {
            "total_students": len(student_ids),
            "job_title": interview_data.get("job_title", ""),
            "status": "notifications_sent"
        }
    
    def _build_html_email_body(self, name: str, student_email: str, student_phone: str, interview_data: Dict) -> str:
        """Build HTML email body content"""
        # Read HTML template
        template_path = os.path.join(os.path.dirname(__file__), 'email_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            html_template = f.read()
        
        # Prepare data for template
        topics = interview_data.get("topics", "")
        batch = interview_data.get("batch", "")
        week_range = interview_data.get("weekRange", {})
        
        # Format week range
        week_range_str = f"{week_range.get('startDate', '')} to {week_range.get('endDate', '')}"
        
        # Decode HTML entities in links and personalize application link
        base_app_link = html.unescape(interview_data.get("application_link", ""))
        app_link = generate_personalized_interview_link(base_app_link, student_email) if base_app_link else ""
        report_link = html.unescape(interview_data.get("report_link", ""))
        
        # Simple template replacement (for production, consider using Jinja2)
        html_body = html_template.replace('{{name}}', name)
        html_body = html_body.replace('{{job_title}}', interview_data.get('job_title', ''))
        html_body = html_body.replace('{{batch}}', batch)
        html_body = html_body.replace('{{week_range}}', week_range_str)
        html_body = html_body.replace('{{topics}}', topics)
        html_body = html_body.replace('{{sender_email}}', student_email)
        html_body = html_body.replace('{{sender_phone}}', student_phone)
        html_body = html_body.replace('{{deadline_date}}', interview_data.get('deadline_date', ''))
        html_body = html_body.replace('{{company_email}}', self.sender_email)
        
        # Handle conditional links
        if app_link:
            html_body = html_body.replace('{{#if application_link}}', '')
            html_body = html_body.replace('{{/if}}', '')
            html_body = html_body.replace('{{application_link}}', app_link)
        else:
            # Remove application link section
            start = html_body.find('{{#if application_link}}')
            end = html_body.find('{{/if}}', start) + 7
            if start != -1 and end != -1:
                html_body = html_body[:start] + html_body[end:]
        
        if report_link:
            html_body = html_body.replace('{{#if report_link}}', '')
            html_body = html_body.replace('{{/if}}', '')
            html_body = html_body.replace('{{report_link}}', report_link)
        else:
            # Remove report link section
            start = html_body.find('{{#if report_link}}')
            end = html_body.find('{{/if}}', start) + 7
            if start != -1 and end != -1:
                html_body = html_body[:start] + html_body[end:]
        
        return html_body
    
    def _build_text_email_body(self, name: str, student_email: str, interview_data: Dict) -> str:
        """Build plain text email body - must match HTML template"""
        topics = interview_data.get("topics", "")
        batch = interview_data.get("batch", "")
        week_range = interview_data.get("weekRange", {})
        
        base_app_link = html.unescape(interview_data.get("application_link", ""))
        app_link = generate_personalized_interview_link(base_app_link, student_email) if base_app_link else ""
        report_link = html.unescape(interview_data.get("report_link", ""))
        
        email_body = f"""
Dear {name},

You have been scheduled for an week interview based on your recent curriculum progress.

Interview Details:
- Job Title: {interview_data.get('job_title', '')}
- Batch: {batch}
- Week Range: {week_range.get('startDate', '')} to {week_range.get('endDate', '')}
- Topics Covered: {topics}
"""
        
        if app_link:
            email_body += f"\n- Application Link: {app_link}"
        if report_link:
            email_body += f"\n- Report Link: {report_link}"
            
        email_body += f"\n\nNote: Please use your LMS credentials to login and book your interview slot.\nUse the application link above to book your interview slot.\n\nImportant Guidelines:\n- Avoid using Bluetooth devices or headphones during the interview.\n- If you face any issues while taking Interviews on a Laptop, use your Mobile\n- Everyone needs to complete the test by {interview_data.get('deadline_date', '')}\n\nStudents who faced any issues while using the AI Mock Interview Platform are requested to record their screen showing the problem and share the recording with us. Only the profiles with valid screen recordings will be rechecked.\n\nBest regards,\nCodegnan Team\n"
        
        return email_body
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send email via SMTP with both HTML and text versions"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach both text and HTML versions
            msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"SMTP Error: {e}")
            return False
    
    def __del__(self):
        """Cleanup thread pool on destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)