import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

def sendmail(to,subject,body,name,s3_url):
    import requests
    # SMTP Configuration
    smtp_server = os.getenv("SMTP_SERVER", "email-smtp.us-east-1.amazonaws.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = 'placements@codegnan.com'
    
    # Validate required credentials
    if not smtp_username or not smtp_password:
        raise Exception("SMTP credentials not configured in environment variables")
    
    subject =subject
    text=body
    name=name.strip()
    
    # Download PDF from S3 URL
    try:
        response = requests.get(s3_url, timeout=30)
        response.raise_for_status()
        pdf_data = response.content
    except Exception as e:
        raise Exception(f"Failed to download PDF from S3: {e}")
    msg = MIMEMultipart()
    msg['From'] = f'Codegnan IT Solutions <{sender_email}>'
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    
    # Validate PDF content (basic check)
    if len(pdf_data) < 100 or not pdf_data.startswith(b'%PDF'):
        raise Exception("Invalid or corrupted PDF file from S3")
    
    # Create attachment with proper PDF MIME type
    part = MIMEBase('application', 'pdf')
    part.set_payload(pdf_data)
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename="{name.strip()}.pdf"'
    )
    msg.attach(part)
    # Server connection with proper error handling
    mailserver = None
    try:
        mailserver = smtplib.SMTP(smtp_server, smtp_port)
        mailserver.starttls()
        mailserver.login(smtp_username, smtp_password)
        mailserver.sendmail(sender_email, to, msg.as_string())
    finally:
        if mailserver:
            try:
                mailserver.quit()
            except:
                pass  # Ignore errors during cleanup