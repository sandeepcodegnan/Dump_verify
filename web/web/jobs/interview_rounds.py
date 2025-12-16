from flask_restful import Resource
from web.jwt.auth_middleware import bde_required
from flask import request
import os, smtplib, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from web.db.db_utils import get_collection

job_collection = get_collection('jobs')
student_collection = get_collection('students')

class InterviewRounds(Resource):
    def __init__(self):
        super().__init__()
        self.smtp_server = os.getenv("SMTP_SERVER", "email-smtp.us-east-1.amazonaws.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = 'placements@codegnan.com'
        

    def send_email(self, to_email, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False

    def get_selected_template(self, student_name, company_name, job_role, comment=None):
        return f"""<html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="x-apple-disable-message-reformatting">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Congratulations - Codegnan Destination</title>
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
                    <style>
                    @media only screen and (max-width: 768px) {{
                        .outer-pad {{ padding: 12px 8px !important; }}
                        .card-pad  {{ padding: 16px !important; }}
                        .footer-pad{{ padding: 0 16px !important; }}
                        .social-cell {{ padding: 0 6px !important; }}
                        .social-icon {{ width: 32px !important; height: 32px !important; }}
                        h1, h2 {{ font-size: 18px !important; }}
                        body, p, td {{ font-size: 13px !important; line-height: 1.5 !important; }}
                        .signature {{ text-align: center !important; }}
                    }}
                    @media only screen and (max-width: 991px) {{
                        .stack-col {{ display:block !important; width:100% !important; }}
                        .stack-center {{ text-align:center !important; }}
                        .contact-gap {{ padding-top:8px !important; }}
                    }}
                    /* Show mobile layout and hide desktop layout on small screens < 600px */
                    @media only screen and (max-width: 599px) {{
                        .desktop-phone {{ display:none !important; }}
                        .mobile-phone-stack {{ display:block !important; }}
                    }}
                    /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
                    @media only screen and (min-width: 600px) {{
                        .desktop-phone {{ display:block !important; }}
                        .mobile-phone-stack {{ display:none !important; }}
                    }}
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
                                    Dear <strong>{student_name}</strong>,
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                                    {comment}
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
                </html>"""

    def get_rejected_template(self, student_name, company_name, comment=None):
        return f"""<html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="x-apple-disable-message-reformatting">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Application Update - Codegnan Destination</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <!--[if mso]>
                <style type="text/css">
                    body, table, td, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
                </style>
                <![endif]-->
            <!--[if !mso]><!-->
            <style>
                /* Tablet & mobile text + padding tweaks */
                @media only screen and (max-width: 768px) {{
                .outer-pad {{
                    padding: 12px 8px !important;
                }}

                .card-pad {{
                    padding: 16px !important;
                }}

                .panel-pad {{
                    padding: 12px !important;
                }}

                .footer-pad {{
                    padding: 0 16px !important;
                }}

                .social-wrap {{
                    margin: 10px auto 8px auto !important;
                }}

                .social-cell {{
                    padding: 0 6px !important;
                }}

                .social-icon {{
                    width: 32px !important;
                    height: 32px !important;
                }}

                h2 {{
                    font-size: 17px !important;
                }}

                h3 {{
                    font-size: 15px !important;
                }}

                body,
                p,
                td {{
                    font-size: 13px !important;
                    line-height: 1.5 !important;
                }}

                .signature {{
                    text-align: center !important;
                }}
                }}

                /* Stack phone + website vertically on screens < 992px */
                @media only screen and (max-width: 991px) {{
                .stack-col {{
                    display: block !important;
                    width: 100% !important;
                }}

                .stack-center {{
                    text-align: center !important;
                }}

                .contact-gap {{
                    padding-top: 8px !important;
                }}
                }}

                /* Show mobile layout and hide desktop layout on small screens < 600px */
                @media only screen and (max-width: 599px) {{
                .desktop-phone {{
                    display: none !important;
                }}

                .mobile-phone-stack {{
                    display: block !important;
                }}
                }}

                /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
                @media only screen and (min-width: 600px) {{
                .desktop-phone {{
                    display: block !important;
                }}

                .mobile-phone-stack {{
                    display: none !important;
                }}
                }}
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
                            Important Update Regarding Your Application with {company_name}
                        </h2>

                        <!-- Body -->
                        <table role="presentation" width="100%" style="font-size:15px;color:#374151;">
                            <tr>
                            <td style="padding-bottom:12px;">Dear {student_name},</td>
                            </tr>
                            <tr>
                            <td style="padding-bottom:12px;">
                                {comment}
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
                                    <td style="padding:3px 0;">• <strong>Soft Skills & Networking:</strong> Strengthen
                                    communication and problem-solving; connect with mentors.</td>
                                </tr>
                                <tr>
                                    <td style="padding:3px 0;">• <strong>Engage & Practice:</strong> Participate in classes,
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
            </html>"""


    def get_final_template(self, student_name, company_name, job_role, comment=None):
        return f"""<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Application Finalised - Codegnan Destination</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <!--[if mso]>
      <style type="text/css">
        body, table, td, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
      </style>
    <![endif]-->
    <style>
      @media only screen and (max-width: 768px) {{
        .outer-pad {{ padding: 12px 8px !important; }}
        .card-pad  {{ padding: 16px !important; }}
        .footer-pad{{ padding: 0 16px !important; }}
        .social-cell {{ padding: 0 6px !important; }}
        .social-icon {{ width: 32px !important; height: 32px !important; }}
        h1,h2 {{ font-size: 18px !important; }}
        h3 {{ font-size: 15px !important; }}
        body, p, td {{ font-size: 13px !important; line-height: 1.5 !important; }}
        .signature {{ text-align: center !important; }}
      }}
      @media only screen and (max-width: 991px) {{
        .stack-col {{ display:block !important; width:100% !important; }}
        .stack-center {{ text-align:center !important; }}
        .contact-gap {{ padding-top:8px !important; }}
      }}
      /* Show mobile layout and hide desktop layout on small screens < 600px */
      @media only screen and (max-width: 599px) {{
        .desktop-phone {{ display:none !important; }}
        .mobile-phone-stack {{ display:block !important; }}
      }}
      /* Show desktop layout and hide mobile layout on larger screens ≥ 600px */
      @media only screen and (min-width: 600px) {{
        .desktop-phone {{ display:block !important; }}
        .mobile-phone-stack {{ display:none !important; }}
      }}
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

                <!-- HEADER (common) -->
                <table role="presentation" width="100%">
                  <tr>
                    <td align="center" style="padding:0 0 16px 0;">
                      <img src="https://codegnan.com/wp-content/uploads/2025/04/cropped-Codegnan-Destination-New-Logo-e1745992388557.png" alt="Codegnan Destination Logo" height="56" style="display:block; height:56px; width:auto; max-width:100%; border:0;">
                    </td>
                  </tr>
                </table>

                <!-- BODY (Finalised) -->
                <table role="presentation" width="100%">
                  <tr>
                    <td align="center" style="padding-bottom:12px;">
                      <h2 style="margin:0; font-size:20px; font-weight:600; color:#16A34A;">Application Finalised 🎉</h2>
                    </td>
                  </tr>
                  <tr>
                    <td align="center" style="padding-bottom:16px;">
                      <h3 style="margin:0; font-size:16px; font-weight:600; color:#111827;">
                        Your Application is Finalised for {company_name} 🎉
                      </h3>
                    </td>
                  </tr>

                  <tr>
                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                      Dear <strong>{student_name}</strong>,
                    </td>
                  </tr>

                  <tr>
                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                      We are absolutely delighted to inform you that your application process has been officially finalised for <strong>{job_role}</strong> with our hiring partner, <strong>{company_name}</strong>.
                    </td>
                  </tr>

                  <tr>
                    <td style="font-size:15px; color:#374151; padding-bottom:12px;">
                      Congratulations on this fantastic achievement. We are incredibly proud of the hard work and dedication you showed throughout the entire selection process.
                    </td>
                  </tr>

                  <tr>
                    <td align="center" style="font-size:15px; color:#374151; padding-bottom:12px;">
                      We wish you the very best for the next stage of the process.
                    </td>
                  </tr>
                  <tr>
                    <td class="signature" style="padding-top:18px; color:#374151; font-size:15px; text-align:center;">
                      Best regards,<br><strong>Team Codegnan</strong>
                    </td>
                  </tr>
                </table>

                <!-- Divider -->
                <table role="presentation" width="100%" style="margin:28px 0;">
                  <tr><td style="border-top:1px solid #E5E7EB; height:1px; line-height:1px; font-size:0;">&nbsp;</td></tr>
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
            <tr><td style="height:12px; line-height:12px; font-size:12px;">&nbsp;</td></tr>
          </table>

        </td>
      </tr>
    </table>

  </body>
</html>"""


    def get_student_emails(self, student_ids):
        students = student_collection.find({"id": {"$in": student_ids}}, {"id": 1,"name": 1,"studentId":1,"email": 1, "studentPhNumber": 1, "highestGraduationpercentage": 1, "department": 1, "location": 1, "yearOfPassing": 1,"studentSkills":1,"resume_url":1})
    
        return {student["id"]: {"email": student["email"],"students_id":student["studentId"],"name": student["name"],"studentPhNumber":student["studentPhNumber"],"department":student["department"],"highestGraduationpercentage":student["highestGraduationpercentage"],"location":student["location"],"yearOfPassing":student["yearOfPassing"],"studentSkills":student.get('studentSkills'),"resume_url":student.get('resume_url')} for student in students}
    @bde_required
    def post(self):
        data = request.get_json()
        job_id = data.get('job_id')
        round_number = data.get('round_number')
        selected_ids = data.get('selected_students', [])
        rejected_ids = data.get('rejected_students', [])
        select_comment = data.get('selected_comment')
        reject_comment = data.get('rejected_comment')   
        
        if not job_id:
            return {"error": "Missing 'job_id'"}, 401
        if not round_number:
            return {"error": "Missing 'round_number'"}, 401
        if not selected_ids and not rejected_ids:
            return {"error": "No students selected or rejected"}, 401

        job = job_collection.find_one({"id": job_id})
        if not job:
            return {"error": "Job not found"}, 404
            
        # Check if round already exists
        round_key = f"round_{round_number}"
        existing_rounds = job.get("interview_rounds", {})
        if round_key in existing_rounds:
            return {"error": f"Round {round_number} already completd for this job"}, 302

        # Update job document with round-wise data
        round_key = f"round_{round_number}"
        update_data = {
            f"interview_rounds.{round_key}.selected": selected_ids,
            f"interview_rounds.{round_key}.rejected": rejected_ids,
            f"interview_rounds.{round_key}.selected_comment": select_comment,
            f"interview_rounds.{round_key}.rejected_comment": reject_comment,
            f"interview_rounds.{round_key}.updated_at": datetime.now().isoformat()
        }


        job_collection.update_one({"id": job_id}, {"$set": update_data})

        # Send emails in background thread
        def send_emails_background():
            all_student_ids = selected_ids + rejected_ids
            student_data = self.get_student_emails(all_student_ids)
            
            is_final = data.get('final_round', False)
            
            for student_id in selected_ids:
                if student_id in student_data:
                    student = student_data[student_id]
                    
                    if is_final:
                        subject = f"Application Finalised - Congratulations! {job['designation']} at {job['companyName']}"
                        body = self.get_final_template(student['name'], job['companyName'], job['designation'], select_comment)
                    else:
                        subject = f"Congratulations - Round {round_number} Selected for {job['designation']} at {job['companyName']}"
                        body = self.get_selected_template(student['name'], job['companyName'], job['designation'], select_comment)
                    
                    self.send_email(student['email'], subject, body)
                    print(f"{'Final selection' if is_final else 'Selected'} Email:-- {student['email']}")

            for student_id in rejected_ids:
                if student_id in student_data:
                    student = student_data[student_id]
                    
                    subject = f"Application Update - {job['designation']} at {job['companyName']}"
                    body = self.get_rejected_template(student['name'], job['companyName'], reject_comment)
                    
                    self.send_email(student['email'], subject, body)
                    print(f"{'Final rejection' if is_final else 'Rejected'} Email:-- {student['email']}")
        
        threading.Thread(target=send_emails_background, daemon=True).start()

        message = f"Final round completed - Job offers sent!" if data.get('final_round', False) else f"Round {round_number} updated successfully"
        return {
            "message": message,
            "email_status": "Emails are being sent in background"
        }, 200

    #getting data based job_id and no.of rounds data
    @bde_required
    def get(self):
        job_id = request.args.get('job_id')
        round_number = request.args.get('rounds')
        
        if not job_id:
            return {"error": "Missing 'job_id' parameter"}, 400

        job = job_collection.find_one({"id": job_id}, {"interview_rounds": 1, "_id": 0})
        interview_rounds = job.get("interview_rounds", {}) if job else {}
        
        if not round_number:
            # Return count and round names
            return {
                "total_rounds": len(interview_rounds),
                "rounds": list(interview_rounds.keys())
            }, 200
        
        # Return complete data for specific round
        round_key = f"round_{round_number}"
        if round_key not in interview_rounds:
            return {"error": f"Round {round_number} not found"}, 404
            
        round_data = interview_rounds[round_key]
        
        # Get student details for selected and rejected lists
        selected_ids = round_data.get('selected', [])
        rejected_ids = round_data.get('rejected', [])
        all_ids = selected_ids + rejected_ids
        
        student_details = self.get_student_emails(all_ids)
        
        return {
            "round_number": round_number,
            "selected_students": [{
                "id": sid,
                "name": student_details.get(sid, {}).get('name'),
                "email": student_details.get(sid, {}).get('email'),
                "student_id":student_details.get(sid, {}).get('students_id'),
                "studentPhNumber":student_details.get(sid, {}).get('studentPhNumber'),
                "highestGraduationpercentage":student_details.get(sid, {}).get('highestGraduationpercentage'),
                "department":student_details.get(sid, {}).get('department'),
                "location":student_details.get(sid, {}).get('location'),
                "yearOfPassing":student_details.get(sid, {}).get('yearOfPassing'),
                "studentSkills":student_details.get(sid, {}).get('studentSkills'),
                "resume_url":student_details.get(sid, {}).get("resume_url")
            } for sid in selected_ids],
            "rejected_students": [{
                "id": rid,
                "name": student_details.get(rid, {}).get('name'),
                "email": student_details.get(rid, {}).get('email'),
                "student_id":student_details.get(rid, {}).get('students_id'),
                "studentPhNumber":student_details.get(rid, {}).get('studentPhNumber'),
                "highestGraduationpercentage":student_details.get(rid, {}).get('highestGraduationpercentage'),
                "department":student_details.get(rid, {}).get('department'),
                "location":student_details.get(rid, {}).get('location'),
                "yearOfPassing":student_details.get(rid, {}).get('yearOfPassing'),
                "studentSkills":student_details.get(rid, {}).get('studentSkills'),
                "resume_url":student_details.get(rid, {}).get("resume_url")
            } for rid in rejected_ids],
            "selected_comment": round_data.get('selected_comment'),
            "rejected_comment": round_data.get('rejected_comment')
        }, 200