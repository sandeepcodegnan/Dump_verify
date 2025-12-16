from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from web.db.db_utils import get_collection
import uuid
from datetime import datetime, timezone
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html, os, re
from dotenv import load_dotenv

load_dotenv()
class JobEmailSender(threading.Thread):
    def __init__(self, job_data, student_contacts):
        super().__init__()
        self.job_data = job_data
        self.student_contacts = student_contacts
        cnt=0
        job_skills = set(s.lower() for s in self.job_data.get("jobSkills", []))
        for student in self.student_contacts:
            # Check placement status
            placed = student.get("placed") is True
            placement_status = student.get("placementStatus") is False
            if placed or placement_status:
                continue
                
            # Check dropout status
            batch_no = student.get("BatchNo", "")
            if batch_no.startswith("DROPOUTS-"):
                continue
            
            # Check BatchNo matches job stack
            job_stacks = self.job_data.get("stack", [])
            if job_stacks:
                batch_prefix = batch_no.split('-')[0] if '-' in batch_no else batch_no
                if batch_prefix not in job_stacks:
                    continue
            
            # Percentage
            try:
                percentage_ok = student.get("highestGraduationpercentage", 0) >= float(self.job_data.get("percentage", 0))
            except (ValueError, TypeError):
                percentage_ok = False
            
            # Skills
            student_skills = set(s.lower() for s in student.get("studentSkills", []))
            skills_match = bool(job_skills & student_skills)  # Check intersection
            
            # Graduation year
            allowed_years = set(str(y) for y in self.job_data.get("graduates", []))
            year_ok = str(student.get("yearOfPassing")) in allowed_years

            # Department/branch
            branch_ok = False
            stu_dept_lower = student.get("department", "").lower()
            job_departments = self.job_data.get("department", [])
            
            # Check if "Any Branch" is in the job departments
            if any(dept and dept.lower() == "any branch" for dept in job_departments):
                branch_ok = True  # Accept all students regardless of department
            else:
                # Check if student's department matches any job department
                for dept_entry in job_departments:
                    if not dept_entry:
                        continue
                    if stu_dept_lower == dept_entry.lower():
                        branch_ok = True
                        break

            # Check BatchNo matches job stack for final validation
            stack_match = True
            if job_stacks:
                batch_prefix = batch_no.split('-')[0] if '-' in batch_no else batch_no
                stack_match = batch_prefix in job_stacks
            
            if percentage_ok and skills_match and year_ok and branch_ok and stack_match:
                self.send_email(student["email"], student["name"], student["id"], self.job_data)
                cnt += 1

    def send_email(self, email, name, student_id, job_data):
        try:
            safe_company = html.escape(str(job_data.get('companyName', 'Company')))
            safe_name = html.escape(str(name))
            safe_role = html.escape(str(job_data.get('jobRole', 'N/A')))
            safe_location = html.escape(str(job_data.get('jobLocation', 'N/A')))
            safe_salary = html.escape(str(job_data.get('salary', 'N/A')))
            safe_deadline = html.escape(str(job_data.get('deadLine', 'N/A')))
            
            # Comprehensive HTML email template
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">

            <head>
            <meta charset="UTF-8">
            <meta name="x-apple-disable-message-reformatting">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Job Opening - Codegnan Destination</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <!--[if mso]>
                <style type="text/css">
                    body, table, td, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
                </style>
                <![endif]-->
            <style>
                @media only screen and (max-width: 768px) {{
                .outer-pad {{ padding: 12px 8px !important; }}
                .card-pad {{ padding: 16px !important; }}
                .footer-pad {{ padding: 0 16px !important; }}
                .social-cell {{ padding: 0 6px !important; }}
                .social-icon {{ width: 32px !important; height: 32px !important; }}
                h2 {{ font-size: 18px !important; }}
                h3 {{ font-size: 15px !important; }}
                body, p, td {{ font-size: 13px !important; line-height: 1.5 !important; }}
                .job-title {{ font-size: 16px !important; }}
                .btn {{ font-size: 14px !important; padding: 8px 14px !important; }}
                .text-center-sm {{ text-align: center !important; }}
                .details-table {{ font-size: 13px !important; }}
                }}

                /* Show mobile layout and hide desktop layout on small screens < 600px */
                @media only screen and (max-width: 599px) {{
                .desktop-phone {{ display: none !important; }}
                .mobile-phone-stack {{ display: block !important; }}
                }}

                /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
                @media only screen and (min-width: 600px) {{
                .desktop-phone {{ display: block !important; }}
                .mobile-phone-stack {{ display: none !important; }}
                }}

                .btn {{
                display: inline-block;
                padding: 10px 18px;
                border-radius: 8px;
                border: 1px solid #4f46e5;
                background: transparent;
                color: #4f46e5;
                text-decoration: none;
                font-weight: 600;
                font-size: 15px;
                }}
            </style>
            </head>

            <body style="margin:0;padding:0;background:#f9fafb;color:#252b37;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;font-family:'Inter',Arial,Helvetica,sans-serif;line-height:1.6;">

            <!-- Preheader -->
            <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">
                New job posted that matches your profile.
            </div>

            <!-- Background -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f9fafb;width:100%;">
                <tr>
                <td align="center" class="outer-pad" style="padding:24px 12px;">

                    <!-- Main Card -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                    style="max-width:760px;background:#ffffff;border-radius:12px;border:1px solid #e5e7eb;box-shadow:0 1px 3px rgba(10,13,18,.10),0 1px 2px rgba(10,13,18,.06);">
                    <tr>
                        <td class="card-pad" style="padding:32px;">

                        <!-- Logo -->
                        <table role="presentation" width="100%">
                            <tr>
                            <td align="center" style="padding-bottom:20px;">
                                <img
                                src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png"
                                alt="Codegnan Destination Logo" height="56" style="display:block;height:56px;width:auto;max-width:100%;border:0;">
                            </td>
                            </tr>
                        </table>

                        <!-- Body -->
                        <h2 class="text-center-sm" style="margin:0 0 8px 0;font-size:24px;line-height:1.35;font-weight:600;color:#3238a3;text-align:center;">
                            Job Opening
                        </h2>

                        <p class="job-title" style="margin:8px 0 18px 0;font-size:22px;line-height:1.3;color:#111827;text-align:center;font-weight:600;">
                            {safe_role} at <strong>{safe_company}</strong>
                        </p>

                        <table role="presentation" width="100%" style="font-size:17px;color:#374151;margin-bottom:12px;">
                            <tr>
                            <td style="padding-bottom:12px;">Dear <strong>{safe_name}</strong>,</td>
                            </tr>
                            <tr>
                            <td style="padding-bottom:12px;">
                                We have a new position available at <strong>{safe_company}</strong> that matches your profile.
                            </td>
                            </tr>
                        </table>

                        <table role="presentation" width="100%" style="margin-top:8px;">
                            <tr>
                            <td style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px;">
                                <table role="presentation" width="100%" class="details-table" style="font-size:16px;color:#374151;">
                                <tr>
                                    <td colspan="2" style="padding:6px 0;color:#111827;font-weight:700;">Details:</td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-weight:600;">Position</td>
                                    <td style="padding:6px 0;"><strong>: {safe_role}</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-weight:600;">Location</td>
                                    <td style="padding:6px 0;"><strong>: {safe_location}</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-weight:600;">Salary</td>
                                    <td style="padding:6px 0;"><strong>: {safe_salary}</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-weight:600;">Deadline</td>
                                    <td style="padding:6px 0;"><strong>: {safe_deadline}</strong></td>
                                </tr>
                                </table>
                            </td>
                            </tr>
                        </table>

                        <p style="text-align:center;margin:18px 0 8px 0;font-size:16px;color:#6b7280;">
                            Please review the details and apply if interested
                        </p>

                        <div style="text-align:center;margin-bottom:18px;">
                            <a href="https://placements.codegnan.com" class="btn">View Job Details</a>
                        </div>

                        <p style="margin-top:8px;font-size:17px;color:#374151;text-align:center;">
                            Best regards,<br><strong>Codegnan Placements Team</strong>
                        </p>

                        <!-- Divider -->
                        <table role="presentation" width="100%" style="margin:22px 0;">
                            <tr>
                            <td style="border-top:1px solid #E5E7EB;height:1px;line-height:1px;font-size:0;">&nbsp;</td>
                            </tr>
                        </table>

                        <!-- Footer -->
                        <table role="presentation" width="100%">
                            <tr>
                            <td align="center" style="color:#6b7280;font-size:14px;">
                                <div class="footer-pad" style="padding:0 32px;">

                                <!-- Social Icons -->
                                <table role="presentation" align="center" style="margin:14px auto 12px auto;">
                                    <tr>
                                    <td style="padding:0 10px;">
                                        <a href="https://www.facebook.com/codegnan/">
                                        <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318314-1.png"
                                            width="36" height="36" alt="Facebook" style="display:block;border:0;">
                                        </a>
                                    </td>
                                    <td style="padding:0 10px;">
                                        <a href="https://www.youtube.com/codegnan">
                                        <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318313.png" width="36"
                                            height="36" alt="YouTube" style="display:block;border:0;">
                                        </a>
                                    </td>
                                    <td style="padding:0 10px;">
                                        <a href="https://in.linkedin.com/company/codegnan">
                                        <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318312.png" width="36"
                                            height="36" alt="LinkedIn" style="display:block;border:0;">
                                        </a>
                                    </td>
                                    </tr>
                                </table>

                                <!-- Contact Info -->
                                <table role="presentation" width="100%" style="max-width:520px;margin:10px auto 0 auto;text-align:center;">
                                    <tr>
                                    <td align="center" style="padding:6px 0;font-size:14px;color:#6b7280;text-align:center;">
                                        📍 <a href="https://www.google.com/maps/place/Codegnan+Vijayawada/data=!4m2!3m1!1s0x0:0xe6ed5ede725b304b?sa=X&ved=1t:2428&ictx=111"
                                        style="color:#2563eb; text-decoration:none; border-bottom:1px solid #d1d5db;">Codegnan IT Solutions</a>
                                    </td>
                                    </tr>

                                    <tr>
                                    <td align="center" style="padding:6px 0;font-size:14px;color:#6b7280;text-align:center;">
                                        🌐 <a href="https://codegnan.com/"
                                        style="color:#2563eb; text-decoration:none; border-bottom:1px solid #d1d5db;">www.codegnan.com</a>
                                    </td>
                                    </tr>

                                    <!-- Phone Numbers - Responsive Layout -->
                                    <tr>
                                    <td align="center" style="padding:6px 0;">
                                        <!-- Desktop Layout (≥600px) -->
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;"
                                        class="desktop-phone">
                                        <tr>
                                            <td align="center" style="padding:3px 8px; font-size:14px; color:#6b7280;">
                                            📞 <span style="border-bottom:1px solid #d1d5db;">Hyderabad - +91 8977 544 092</span>
                                            </td>
                                            <td align="center" style="padding:3px 8px; font-size:14px; color:#6b7280;">
                                            📞 <span style="border-bottom:1px solid #d1d5db;">Hyderabad - +91 9642 988 788</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="padding:3px 8px; font-size:14px; color:#6b7280;">
                                            📞 <span style="border-bottom:1px solid #d1d5db;">Vijayawada - +91 9642 988 688</span>
                                            </td>
                                            <td align="center" style="padding:3px 8px; font-size:14px; color:#6b7280;">
                                            📞 <span style="border-bottom:1px solid #d1d5db;">Bengaluru - +91 98887 38888</span>
                                            </td>
                                        </tr>
                                        </table>

                                        <!-- Mobile Layout (<600px) -->
                                        <div class="mobile-phone-stack" style="display:none;">
                                        <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Hyderabad</div>
                                        <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 8977 544 092</span></div>
                                        <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 9642 988 788</span></div>

                                        <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Vijayawada -</div>
                                        <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 9642 988 688</span></div>

                                        <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Bengaluru -</div>
                                        <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 98887 38888</span></div>
                                        </div>
                                    </td>
                                    </tr>

                                    <!-- Logo -->
                                    <tr>
                                    <td align="center" style="padding:12px 0 0 0;text-align:center;">
                                        <img
                                        src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png"
                                        alt="Codegnan" height="32" style="display:block;height:32px;width:auto;opacity:.9;border:0;margin:0 auto;">
                                    </td>
                                    </tr>
                                </table>

                                </div>
                            </td>
                            </tr>
                        </table>


                        </td>
                    </tr>
                    </table>
                </td>
                </tr>
            </table>

            </body>

            </html>
            """

            # Email configuration with AWS SES environment variables
            smtp_server_host = os.getenv('SMTP_SERVER', 'email-smtp.us-east-1.amazonaws.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            sender_email = 'placements@codegnan.com'
            
            if not smtp_username or not smtp_password:
                return False
                
            recipient_email = email
            subject = f"Job Opening: {safe_role} at {safe_company}"

            # Create message container
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Codegnan Placements <{sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg['Reply-To'] = sender_email
            # Add headers to indicate this is transactional, not promotional
            msg['X-Priority'] = '3'
            msg['X-MSMail-Priority'] = 'Normal'

            # Attach HTML content to the email
            msg.attach(MIMEText(html_content, 'html'))

            # Send email using AWS SES SMTP
            with smtplib.SMTP(smtp_server_host, smtp_port) as smtp_server:
                smtp_server.starttls()
                smtp_server.login(smtp_username, smtp_password)
                smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
            return True
        except smtplib.SMTPException as e:
            return False
        except Exception as e:
            return False

class JobPosting(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('jobs')
        self.student_collection = get_collection('students')
    
    @bde_required
    def post(self):
        # Extract data from the request
        data = request.get_json()
        id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        companyName = data.get('companyName')
        jobRole = data.get('jobRole')
        graduates = data.get('graduates')
        salary = data.get('salary')
        educationQualification = data.get('educationQualification')
        department = data.get('department')
        percentage = int(data.get('percentage'))
        bond = data.get('bond')
        jobLocation = data.get('jobLocation')
        specialNote = data.get("specialNote")
        deadLine = data.get("deadLine")
        designation=data.get("designation", "")
        jobSkills = data.get("jobSkills", [])
        BDE_Id = data.get('BDEId')
        location = data.get('location')
        interview_mode = data.get('interviewMode')
        stack = data.get('stack')

        # Collections are already initialized in db_utils

        job_data = {
            "id": id,
            "timestamp": timestamp,
            "companyName": companyName,
            "jobRole": jobRole,
            "graduates": data.get('graduates', []),
            "salary": salary,
            "educationQualification": educationQualification,
            "department": department,
            "percentage": percentage,
            "bond": bond,
            "jobLocation": jobLocation,
            "specialNote": specialNote,
            "deadLine": deadLine,
            "jobSkills": jobSkills,
            "designation":designation,
            "Job_posting_BDE_Id": BDE_Id , # Adding student_id to the job_data
            "Mode_of_Interview":interview_mode,
            "Job_posting_Location":location,
            "stack":stack
        }
        
        result = self.collection.insert_one(job_data)
        job_data['_id'] = str(result.inserted_id)


        response = {"message": "Job posting successful", "job_posting": job_data}
        
        # Start a background thread for email sending
        threading.Thread(target=self.send_emails_in_background, args=(job_data,)).start()

        return response, 200
 
    def send_emails_in_background(self, job_data):
        """Fetch students and send emails in the background."""
        try:            
            student_contacts_cursor = self.student_collection.find({}, {"email": 1, "name": 1, "id": 1, "highestGraduationpercentage": 1,"studentSkills":1,"department":1,"yearOfPassing":1,"placed":1,"placementStatus":1,"BatchNo":1})
            student_contacts = [student for student in student_contacts_cursor]

            # Start a thread to send emails
            email_sender_thread = JobEmailSender(job_data, student_contacts)
            email_sender_thread.start()
        except Exception as e:
            print(f"Error in send_emails_in_background: {e}")