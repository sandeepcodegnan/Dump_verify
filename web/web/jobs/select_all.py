import smtplib,os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import request, render_template_string
from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
import threading
from flask import current_app
from web.db.db_utils import get_collection, get_db

class UpdateJobApplicants(Resource):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.job_collection = get_collection('jobs')
        self.student_collection = get_collection('students')
        self.bde_collection = get_collection('bde')
        self.placement_logs_collection = self.db['Placements_Data']

    @bde_required
    def post(self):
        try:
            data = request.get_json()
            # print('--------------------------',data)
            job_id = data.get('job_id')
            selected_student_ids = data.get('selected_student_ids', [])
            selecet_comment = data.get('selected_comment')
            reject_comment = data.get('rejected_comment')

            # Retrieve the job document
            job_document = self.job_collection.find_one({"id": job_id})
            if not job_document:
                return {"error": "Job not found with the provided job_id"}, 404

            # Determine selected vs rejected
            applicants_ids = job_document.get('applicants_ids', [])
            selected_students = {"selected_comment": selecet_comment, "students": list(set(selected_student_ids))}
            rejected_students = {"rejected_comment": reject_comment, "students": list(set(applicants_ids) - set(selected_student_ids))}

            # Update the job document
            update_result = self.job_collection.update_one(
                {"id": job_id},
                {"$set": {
                    "selected_students_ids": selected_students,
                    "rejected_students_ids": rejected_students
                }}
            )

            if update_result.modified_count < 0:
                return {"error": "Failed to update job applicants"}, 500

            # Update student records synchronously
            selected_ids = selected_students.get("students", [])
            rejected_ids = rejected_students.get("students", [])
            self.update_student_documents(selected_ids, rejected_ids, job_id)
            
            # Log company-wise placement results
            self.log_placement_results(job_document, selected_students, rejected_students)

            # Spawn a daemon thread to send out emails
            company_name = job_document.get('companyName')
            job_position = job_document.get('jobRole')
            app = current_app._get_current_object()
            email_thread = threading.Thread(
                target=self.send_custom_email,
                args=(app,selected_students, rejected_students, company_name, job_position),
                daemon=True)
            email_thread.start()

            return {"message": "Job applicants updated; emails are being sent in background"}, 200

        except Exception as e:
            return {"error": str(e)}, 500
        
    def update_student_documents(self, selected_students, rejected_students, job_id):
        # Update selected students
        for student_id in selected_students:
            self.student_collection.update_one(
                {"id": student_id},
                {"$addToSet": {"selected_jobs": job_id}},
                upsert=True
            )
        # Update rejected students
        for student_id in rejected_students:
            self.student_collection.update_one(
                {"id": student_id},
                {"$addToSet": {"rejected_jobs": job_id}},
                upsert=True
            )

    def send_custom_email(self, app,selected_students, rejected_students, company_name, job_position):
        with app.app_context():
            select_comment = selected_students.get("selected_comment")
            for student_id in selected_students.get("students", []):
                student_document = self.student_collection.find_one({"id": student_id})
                if student_document:
                    name = student_document.get('name')
                    email = student_document.get('email')
                    self.send_email(name, email, company_name, job_position, selected=True, comment=select_comment)
            reject_comment = rejected_students.get("rejected_comment")
            for student_id in rejected_students.get("students", []):
                student_document = self.student_collection.find_one({"id": student_id})
                if student_document:
                    name = student_document.get('name')
                    email = student_document.get('email')
                    self.send_email(name, email, company_name, job_position, selected=False, comment=reject_comment)

            # Send summary email to BDEs
            selected_count = len(selected_students.get("students", []))
            rejected_count = len(rejected_students.get("students", []))
            self.send_summary_email_to_bdes(app,selected_count, rejected_count, company_name, job_position)

    def send_email(self, name, email, company_name, job_position, selected=True, comment=None):
        # Customize email content based on selected or rejected status
        subject = f"Placement Notification - {company_name}"

        if selected:
            # Use professional HTML template for selected students
            message = render_template_string("""
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="x-apple-disable-message-reformatting">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Congratulations - Codegnan Destination</title>
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
                    <style>
                    @media only screen and (max-width: 768px) {
                        .outer-pad { padding: 12px 8px !important; }
                        .card-pad  { padding: 16px !important; }
                        .footer-pad{ padding: 0 16px !important; }
                        .social-cell { padding: 0 6px !important; }
                        .social-icon { width: 32px !important; height: 32px !important; }
                        h1, h2 { font-size: 18px !important; }
                        body, p, td { font-size: 13px !important; line-height: 1.5 !important; }
                        .signature { text-align: center !important; }
                    }
                    @media only screen and (max-width: 991px) {
                        .stack-col { display:block !important; width:100% !important; }
                        .stack-center { text-align:center !important; }
                        .contact-gap { padding-top:8px !important; }
                    }
                    /* Show mobile layout and hide desktop layout on small screens < 600px */
                    @media only screen and (max-width: 599px) {
                        .desktop-phone { display:none !important; }
                        .mobile-phone-stack { display:block !important; }
                    }
                    /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
                    @media only screen and (min-width: 600px) {
                        .desktop-phone { display:block !important; }
                        .mobile-phone-stack { display:none !important; }
                    }
                    </style>
                </head>

                <body style="margin:0; padding:0; background:#f5f6f8; color:#252b37; font-family:'Inter', Arial, Helvetica, sans-serif; line-height:1.6;">

                    <!-- Background -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; background:#f5f6f8;">
                    <tr>
                        <td align="center" class="outer-pad" style="padding:24px 12px;">

                        <!-- Card -->
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:760px; background:#ffffff; border-radius:16px; border:1px solid #E5E7EB; box-shadow:0 1px 3px rgba(10,13,18,.10), 0 1px 2px rgba(10,13,18,.06);">
                            <tr>
                            <td class="card-pad" style="padding:32px;">

                                <!-- Header -->
                                <table role="presentation" width="100%">
                                <tr>
                                    <td align="center" style="padding:0 0 16px 0;">
                                    <img src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png" alt="Codegnan Destination Logo" height="56" style="display:block; height:56px; width:auto; max-width:100%; border:0;">
                                    </td>
                                </tr>
                                </table>

                                <!-- Body -->
                                <table role="presentation" width="100%">
                                <tr>
                                    <td align="center" style="padding-bottom:12px;">
                                    <h2 style="margin:0; font-size:20px; font-weight:600; color:#16A34A;">Congratulations! 🎉</h2>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-bottom:16px;">
                                    <h3 style="margin:0; font-size:16px; font-weight:600; color:#111827;">You have been shortlisted for the next Round.</h3>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                                    Dear <strong>{{name}}</strong>,
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                                    {{comment | safe}}
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size:15px; color:#374151; padding-bottom:12px;">
                                    We wish you the very best for the next stage of the process.
                                    </td>
                                </tr>

                                <tr>
                                    <td class="signature" style="padding-top:18px; text-align:center; color:#374151; font-size:15px;">
                                    Best regards,<br><strong>Team Codegnan</strong>
                                    </td>
                                </tr>
                                </table>

                                <!-- Divider -->
                                <table role="presentation" width="100%" style="margin:28px 0;">
                                <tr><td style="border-top:1px solid #E5E7EB; height:1px; line-height:1px; font-size:0;"> </td></tr>
                                </table>

                                <!-- Footer -->
                                <!-- 📱 Responsive Contact Alignment -->
                                <table role="presentation" width="100%">
                                <tr>
                                    <td align="center" style="color:#6b7280;font-size:14px;">
                                    <div class="footer-pad" style="padding:0 32px;">

                                        <!-- Social Icons -->
                                        <table role="presentation" align="center" style="margin:14px auto 12px auto;">
                                        <tr>
                                            <td style="padding:0 10px;">
                                            <a href="https://www.facebook.com/codegnan/">
                                                <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318314-1.png" width="36" height="36" alt="Facebook" style="display:block;border:0;">
                                            </a>
                                            </td>
                                            <td style="padding:0 10px;">
                                            <a href="https://in.linkedin.com/company/codegnan">
                                                <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318312.png" width="36" height="36" alt="LinkedIn" style="display:block;border:0;">
                                            </a>
                                            </td>
                                            <td style="padding:0 10px;">
                                            <a href="https://www.youtube.com/codegnan">
                                                <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318313.png" width="36" height="36" alt="YouTube" style="display:block;border:0;">
                                            </a>
                                            </td>
                                        </tr>
                                        </table>

                                        <!-- Contact Info -->
                                        <table role="presentation" width="100%" style="max-width:520px;margin:10px auto 0 auto;text-align:center;">
                                        <tr>
                                            <td align="center" style="padding:6px 0;font-size:14px;color:#6b7280;text-align:center;">
                                            📍 <a href="https://www.google.com/maps/place/Codegnan+Vijayawada/data=!4m2!3m1!1s0x0:0xe6ed5ede725b304b?sa=X&ved=1t:2428&ictx=111" style="color:#2563eb; text-decoration:none; border-bottom:1px solid #d1d5db;">Codegnan IT Solutions</a>
                                            </td>
                                        </tr>

                                        <tr>
                                            <td align="center" style="padding:6px 0;font-size:14px;color:#6b7280;text-align:center;">
                                            🌐 <a href="https://codegnan.com/" style="color:#2563eb; text-decoration:none; border-bottom:1px solid #d1d5db;">www.codegnan.com</a>
                                            </td>
                                        </tr>

                                        <!-- Phone Numbers - Responsive Layout -->
                                        <tr>
                                            <td align="center" style="padding:6px 0;">
                                            <!-- Desktop Layout (≥600px) -->
                                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;" class="desktop-phone">
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
                                                <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">Hyderabad</div>
                                                <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span style="border-bottom:1px solid #d1d5db;">+91 8977 544 092</span></div>
                                                <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span style="border-bottom:1px solid #d1d5db;">+91 9642 988 788</span></div>

                                                <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">Vijayawada -</div>
                                                <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span style="border-bottom:1px solid #d1d5db;">+91 9642 988 688</span></div>

                                                <div class="mobile-location" style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">Bengaluru -</div>
                                                <div class="mobile-phone" style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span style="border-bottom:1px solid #d1d5db;">+91 98887 38888</span></div>
                                            </div>
                                            </td>
                                        </tr>

                                        <!-- Logo -->
                                        <tr>
                                            <td align="center" style="padding:12px 0 0 0;text-align:center;">
                                            <img src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png" alt="Codegnan" height="32" style="display:block;height:32px;width:auto;opacity:.9;border:0;margin:0 auto;">
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

                        <!-- Spacer -->
                        <table role="presentation" width="100%">
                            <tr><td style="height:12px; line-height:12px; font-size:12px;"> </td></tr>
                        </table>

                        </td>
                    </tr>
                    </table>

                </body>
                </html>
            """, name=name, job_position=job_position, company_name=company_name, comment=comment)
        else:
            # Use professional HTML template for rejected students
            message = render_template_string("""
                <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="x-apple-disable-message-reformatting">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Application Update - Codegnan Destination</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <!--[if mso]>
                <style type="text/css">
                    body, table, td, a { font-family: Arial, Helvetica, sans-serif !important; }
                </style>
                <![endif]-->
            <!--[if !mso]><!-->
            <style>
                /* Tablet & mobile text + padding tweaks */
                @media only screen and (max-width: 768px) {
                .outer-pad {
                    padding: 12px 8px !important;
                }

                .card-pad {
                    padding: 16px !important;
                }

                .panel-pad {
                    padding: 12px !important;
                }

                .footer-pad {
                    padding: 0 16px !important;
                }

                .social-wrap {
                    margin: 10px auto 8px auto !important;
                }

                .social-cell {
                    padding: 0 6px !important;
                }

                .social-icon {
                    width: 32px !important;
                    height: 32px !important;
                }

                h2 {
                    font-size: 17px !important;
                }

                h3 {
                    font-size: 15px !important;
                }

                body,
                p,
                td {
                    font-size: 13px !important;
                    line-height: 1.5 !important;
                }

                .signature {
                    text-align: center !important;
                }
                }

                /* Stack phone + website vertically on screens < 992px */
                @media only screen and (max-width: 991px) {
                .stack-col {
                    display: block !important;
                    width: 100% !important;
                }

                .stack-center {
                    text-align: center !important;
                }

                .contact-gap {
                    padding-top: 8px !important;
                }
                }

                /* Show mobile layout and hide desktop layout on small screens < 600px */
                @media only screen and (max-width: 599px) {
                .desktop-phone {
                    display: none !important;
                }

                .mobile-phone-stack {
                    display: block !important;
                }
                }

                /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
                @media only screen and (min-width: 600px) {
                .desktop-phone {
                    display: block !important;
                }

                .mobile-phone-stack {
                    display: none !important;
                }
                }
            </style>
            <!--<![endif]-->
            </head>

            <body
            style="margin:0;padding:0;background:#f9fafb;color:#252b37;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;font-family:'Inter',Arial,Helvetica,sans-serif;line-height:1.6;">

            <!-- Preheader -->
            <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">
                Update regarding your application — next steps, tips, and resources from Codegnan.
            </div>

            <!-- Background -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                style="background:#f9fafb;width:100%;">
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
                                alt="Codegnan Destination Logo" height="56"
                                style="display:block;height:56px;width:auto;max-width:100%;border:0;">
                            </td>
                            </tr>
                        </table>

                        <!-- Title -->
                        <h2
                            style="margin:0 0 18px 0;font-size:20px;line-height:1.35;font-weight:600;color:#111827;text-align:center;">
                            Important Update Regarding Your Application with {{company_name}}
                        </h2>

                        <!-- Body -->
                        <table role="presentation" width="100%" style="font-size:15px;color:#374151;">
                            <tr>
                            <td style="padding-bottom:12px;">Dear {{name}},</td>
                            </tr>
                            <tr>
                            <td style="padding-bottom:12px;">
                                {{comment | safe}}
                            </td>
                            </tr>
                        </table>

                        <!-- Comment -->
                        <table role="presentation" width="100%" style="margin-top:16px;">
                            <tr>
                            <td class="panel-pad"
                                style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:16px;">
                                <h3 style="margin:0 0 8px 0;font-size:16px;line-height:1.4;font-weight:600;color:#111827;">💬
                                Placement Officer Comment</h3>
                                <p style="margin:0;font-size:15px;color:#374151;">We understand this news can be disappointing.
                                Remember, every interview and evaluation is a valuable learning experience. Keep sharpening your
                                skills and stay engaged with the tech community — the right opportunity is out there.</p>
                            </td>
                            </tr>
                        </table>

                        <!-- Tips -->
                        <table role="presentation" width="100%" style="margin-top:16px;">
                            <tr>
                            <td class="panel-pad"
                                style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:16px;">
                                <h3 style="margin:0 0 8px 0;font-size:16px;line-height:1.4;font-weight:600;color:#111827;">🚀 Tips
                                for Your Next Opportunity</h3>
                                <p style="margin:0 0 8px 0;font-size:15px;color:#374151;">To help you prepare for future roles
                                across the IT sector, consider focusing on these key areas:</p>
                                <table role="presentation" width="100%" style="font-size:15px;color:#374151;">
                                <tr>
                                    <td style="padding:3px 0;">• <strong>Maximize Visibility:</strong> Keep your placement portal
                                    profile updated with relevant skills and projects.</td>
                                </tr>
                                <tr>
                                    <td style="padding:3px 0;">• <strong>Soft Skills &amp; Networking:</strong> Strengthen
                                    communication and problem-solving; connect with mentors.</td>
                                </tr>
                                <tr>
                                    <td style="padding:3px 0;">• <strong>Engage &amp; Practice:</strong> Participate in classes,
                                    mock interviews, and daily tests.</td>
                                </tr>
                                </table>
                            </td>
                            </tr>
                        </table>

                        <!-- Signature -->
                        <p class="signature" style="margin-top:18px;font-size:15px;color:#374151;text-align:left;">
                            Best regards,<br><strong>Team Codegnan</strong>
                        </p>

                        <!-- Divider -->
                        <table role="presentation" width="100%" style="margin:28px 0;">
                            <tr>
                            <td style="border-top:1px solid #E5E7EB;height:1px;line-height:1px;font-size:0;">&nbsp;</td>
                            </tr>
                        </table>

                        <!-- Footer -->
                        <!-- 📱 Responsive Contact Alignment -->
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
                                            <a href="https://in.linkedin.com/company/codegnan">
                                                <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318312.png" width="36" height="36" alt="LinkedIn" style="display:block;border:0;">
                                            </a>
                                            </td>
                                            <td style="padding:0 10px;">
                                            <a href="https://www.youtube.com/codegnan">
                                                <img src="https://codegnan.com/wp-content/uploads/2025/10/Frame-1321318313.png" width="36" height="36" alt="YouTube" style="display:block;border:0;">
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Contact Info -->
                                <table role="presentation" width="100%"
                                    style="max-width:520px;margin:10px auto 0 auto;text-align:center;">
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
                                        <div class="mobile-location"
                                            style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Hyderabad</div>
                                        <div class="mobile-phone"
                                            style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 8977 544 092</span></div>
                                        <div class="mobile-phone"
                                            style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 9642 988 788</span></div>

                                        <div class="mobile-location"
                                            style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Vijayawada -</div>
                                        <div class="mobile-phone"
                                            style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 9642 988 688</span></div>

                                        <div class="mobile-location"
                                            style="text-align:center; font-weight:600; color:#374151; padding:10px 0 6px 0;">
                                            Bengaluru -</div>
                                        <div class="mobile-phone"
                                            style="text-align:center; padding:4px 0; font-size:14px; color:#6b7280;">📞 <span
                                            style="border-bottom:1px solid #d1d5db;">+91 98887 38888</span></div>
                                        </div>
                                    </td>
                                    </tr>

                                    <!-- Logo -->
                                    <tr>
                                    <td align="center" style="padding:12px 0 0 0;text-align:center;">
                                        <img
                                        src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png"
                                        alt="Codegnan" height="32"
                                        style="display:block;height:32px;width:auto;opacity:.9;border:0;margin:0 auto;">
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

                    <!-- Spacer -->
                    <table role="presentation" width="100%">
                    <tr>
                        <td style="height:12px;line-height:12px;font-size:12px;">&nbsp;</td>
                    </tr>
                    </table>

                </td>
                </tr>
            </table>

            </body>

            </html>
            """, name=name, job_position=job_position, company_name=company_name, comment=comment)

        # Email configuration
        sender_email = "Placements@codegnan.com"

        # Create message container
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject

        # Attach message to email
        msg.attach(MIMEText(message, 'html'))

        # Send email using SMTP (for Gmail)
        try:
            smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) # Update SMTP server details for Gmail
            smtp_server.starttls()
            smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD')) #'Codegnan@0818')  # Update sender's email and password
            smtp_server.sendmail(sender_email, email, msg.as_string())
            smtp_server.quit()
        except Exception as e:
            print("Failed to send email:", e)

    def send_summary_email_to_bdes(self, app, selected_count, rejected_count, company_name, job_position):
        # Retrieve all BDE email addresses
        bde_documents = self.bde_collection.find({})
        bde_emails = [bde.get('email') for bde in bde_documents]

        # Compose the summary email
        subject = f"Summary of Placements for {company_name} - {job_position}"

        message = render_template_string("""
            <p>Dear BDE Team,</p>
            <p>Please find below the summary of the placement results for the position of <strong>{{ job_position }}</strong> at <strong>{{ company_name }}</strong>:</p>
            <p>Number of selected students: {{ selected_count }}</p>
            <p>Number of rejected students: {{ rejected_count }}</p>
            <p>Best regards,</p>
            <p>Codegnan destination placements </p>
            <p>https://placements.codegnan.com</p>                         
        """, company_name=company_name, job_position=job_position, selected_count=selected_count, rejected_count=rejected_count)

        # Email configuration
        sender_email = "Placements@codegnan.com"

        # Create message container
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(bde_emails)
        msg['Subject'] = subject

        # Attach message to email
        msg.attach(MIMEText(message, 'html'))

        # Send email using SMTP (for Gmail)
        try:
            smtp_server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) # Update SMTP server details for Gmail
            smtp_server.starttls()
            smtp_server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD')) #'Codegnan@0818')  # Update sender's email and password
            smtp_server.sendmail(sender_email, bde_emails, msg.as_string())
            smtp_server.quit()
        except Exception as e:
            print("Failed to send email to BDEs:", e)
    
    def log_placement_results(self, job_document, selected_students, rejected_students):
        from datetime import datetime
        
        # Extract student arrays from dictionaries
        selected_student_ids = selected_students.get('students', []) if isinstance(selected_students, dict) else selected_students
        rejected_student_ids = rejected_students.get('students', []) if isinstance(rejected_students, dict) else rejected_students
        
        # Get selected students details
        selected_details = []
        for student_id in selected_student_ids:
            student = self.student_collection.find_one({"id": student_id})
            if student:
                selected_details.append({
                    "id": student_id,
                    "name": student.get('name'),
                    "email": student.get('email')
                })
        
        # Get rejected students details
        rejected_details = []
        for student_id in rejected_student_ids:
            student = self.student_collection.find_one({"id": student_id})
            if student:
                rejected_details.append({
                    "id": student_id,
                    "name": student.get('name'),
                    "email": student.get('email')
                })
        
        log_entry = {
            "company_name": job_document.get('companyName'),
            "job_role": job_document.get('jobRole'),
            "job_id": job_document.get('id'),
            "selected_students": selected_details,
            "rejected_students": rejected_details,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }
        
        self.placement_logs_collection.insert_one(log_entry)
