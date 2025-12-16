from flask_restful import Resource
from flask import request
import os,json
import tempfile
import threading
import queue
import time
from werkzeug.utils import secure_filename
import pandas as pd
import shutil
from web.certificates.PFS_mail import sendmail
import boto3
from botocore import exceptions as bex
from dotenv import load_dotenv
from datetime import datetime
import pytz
from web.jwt.auth_middleware import manager_required
from web.db.db_utils import get_collection, get_db

# Import new PDF generator
try:
    from web.certificates.pdf_generator.integration import generate_certificate_from_replacements
    PDF_GENERATOR_AVAILABLE = True
except ImportError:
    PDF_GENERATOR_AVAILABLE = False

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET = os.getenv('S3_BUCKET_certificates', f'cg-course-completion-certificates')

# Get database and collection from centralized db_utils
db = get_db()
Certificates_collection = get_collection('certificates')

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Cache bucket setup status
_bucket_setup_done = False

def ensure_bucket_exists(bucket_name: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket_name)
        return
    except bex.ClientError as e:
        if e.response['Error']['Code'] in ("404", "NoSuchBucket"):
            create_args = {"Bucket": bucket_name}
            if AWS_REGION != "us-east-1":
                create_args['CreateBucketConfiguration'] = {'LocationConstraint': AWS_REGION}
            s3.create_bucket(**create_args)
        elif e.response['Error']['Code'] == "BucketAlreadyExists":
            return
        else:
            raise

def make_bucket_public(bucket_name: str) -> None:
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
        }],
    }
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))

def setup_bucket():
    global _bucket_setup_done
    if not _bucket_setup_done:
        ensure_bucket_exists(S3_BUCKET)
        make_bucket_public(S3_BUCKET)
        _bucket_setup_done = True

def send_email_sync(email, subject, body, name, s3_url):
    """Send email synchronously and return status"""
    try:
        # Validate inputs
        if not email or not email.strip():
            error_msg = f'Certificate Generated, Email Failed: Invalid email address'
            #print(f"EMAIL DEBUG - {name}: {error_msg}")
            return error_msg
            
        if not s3_url:
            error_msg = f'Certificate Generated, Email Failed: S3 URL not available'
            #print(f"EMAIL DEBUG - {name}: {error_msg}")
            return error_msg
        
        print(f"EMAIL DEBUG - {name}: Attempting to send email to {email}")
        print(f"EMAIL DEBUG - {name}: S3 URL: {s3_url}")
        
        # Use only SMTP via PFS_mail
        sendmail(email, subject, body, name, s3_url)
        #print(f"EMAIL DEBUG - {name}: SMTP Success")
        return 'Success'
    except Exception as email_error:
        error_msg = f'Certificate Generated, Email Failed: {str(email_error)}'
        #print(f"EMAIL DEBUG - {name}: Final error: {error_msg}")
        return error_msg

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def validate_excel_data(excel_file_path):
    """Validate Excel file for missing data in required columns"""
    try:
        data_frame = pd.read_excel(excel_file_path)
        
        # Required columns
        required_columns = ['print_date', 'branch_name', 'name', 'role', 'trainer', 
                          'duration', 'technologies', 'project', 'email', 'studentID']
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in data_frame.columns]
        if missing_columns:
            return False, f"Missing columns: {', '.join(missing_columns)}"
        
        # Check for empty/null values in each required column
        empty_data = {}
        for col in required_columns:
            null_count = data_frame[col].isnull().sum()
            empty_count = (data_frame[col].astype(str).str.strip() == '').sum()
            total_empty = null_count + empty_count
            
            if total_empty > 0:
                empty_rows = data_frame[data_frame[col].isnull() | (data_frame[col].astype(str).str.strip() == '')].index.tolist()
                empty_data[col] = {'count': total_empty, 'rows': [r+2 for r in empty_rows]}  # +2 for Excel row numbers (header + 0-based)
        
        if empty_data:
            error_msg = "Please fill all data and upload again. Missing data found:\n"
            for col, info in empty_data.items():
                error_msg += f"- {col}: {info['count']} empty cells at rows {info['rows']}\n"
            return False, error_msg
        
        return True, "All data is complete"
        
    except Exception as e:
        return False, f"Error reading Excel file: {str(e)}"

def upload_to_s3(file_path, bucket_name, s3_key):
    try:
        #print(f"PROD DEBUG - Uploading {file_path} to S3")
        s3.upload_file(
            file_path,
            bucket_name, 
            s3_key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )
        url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        print(f"PROD DEBUG - S3 upload successful: {url}")
        return url
    except Exception as e:
        print(f"PROD ERROR - S3 upload failed: {str(e)}")
        return None



def generate_certificate_pdf(pdf_path, replacements, name):
    """Generate certificate PDF using new PDF generator"""
    
    if not PDF_GENERATOR_AVAILABLE:
        raise ImportError("PDF Generator module not available")
    
    try:
        #print(f"PROD DEBUG - Processing {name}")
        name = name.strip()
        output_pdf = os.path.join(pdf_path, f"{name}.pdf")
        
        #print(f"PROD DEBUG - Using PDF generator for {name}")
        success = generate_certificate_from_replacements(replacements, output_pdf, name)
        
        if not success:
            raise Exception("PDF generation failed")
        
        print(f"PROD DEBUG - PDF generator successful for {name}")
        
    except Exception as e:
        print(f"PROD ERROR - Certificate generation failed for {name}: {e}")
        raise



def process_certificates_background(excel_file_path, bucket_name=None, batch_no=None):
    """Process certificates in background thread"""
    if bucket_name is None:
        bucket_name = S3_BUCKET
    
    try:
        # Read Excel file
        data_frame = pd.read_excel(excel_file_path)
        
        # Extract data
        p_dat = data_frame['print_date']
        branch = data_frame['branch_name']
        names = data_frame['name'].tolist()
        role = data_frame['role']
        trainer = data_frame['trainer']
        duration = data_frame['duration']
        technologies = data_frame['technologies']
        project = data_frame['project'].tolist()
        emails = data_frame['email'].tolist()
        student_id = data_frame['studentID'].tolist()
        
        # Setup paths - use temp directory for security
        path = tempfile.gettempdir()
        
        # No template needed for new PDF generator
        print(f"PROD DEBUG - Using direct PDF generation (no template required)")
        
        pdf_path = os.path.join(path, 'PFS_certificates')
        
        # Setup S3 bucket once
        setup_bucket()
    
        # Clean and create certificate directory
        if os.path.exists(pdf_path):
            shutil.rmtree(pdf_path)
        os.makedirs(pdf_path, exist_ok=True)
        
        certificates_batch = []
        count = 1
        total_records = len(names)
        
        print(f"PROD DEBUG - Processing {total_records} certificates")
        
        # Process in smaller batches to avoid memory issues
        
        for a, b, c, d, e, f, g, h, i, j in zip(p_dat, branch, names, role, trainer, duration, technologies, project, emails, student_id):
            try:
                p_date = a
                replacements = {
                    "<location>": b.lower().title().strip(),
                    "<name>": c.lower().title().strip(),
                    "<role>": d.strip(),
                    "trainer": e.strip(),
                    "<duration>": f.strip(),
                    "technologies": g.strip(),
                    "o1": h.strip(),
                    "<p1>": p_date
                }
                
                # Progress tracking
                #print(f"PROD DEBUG - Processing {count}/{total_records}: {c.strip()}")
                
                # Generate certificate
                generate_certificate_pdf(pdf_path, replacements, c)
                
                # Small delay for large batches only
                if total_records > 50:
                    time.sleep(0.05)
                
                # Check if PDF was actually created
                pdf_file_path = os.path.join(pdf_path, f"{c.strip()}.pdf")
                
                if not os.path.exists(pdf_file_path):
                    print(f"PROD ERROR - PDF generation failed for {c.strip()}: {pdf_file_path}")
                    email_status = f'Certificate Generation Failed: PDF not created for {c.strip()}'
                    s3_url = None
                else:
                    print(f"PROD DEBUG - PDF created successfully for {c.strip()}")
                    # Upload to S3
                    s3_key = f"certificates/{batch_no}/{c.strip()}.pdf"
                    s3_url = upload_to_s3(pdf_file_path, bucket_name, s3_key)
                    #print(f"PROD DEBUG - S3 upload result for {c.strip()}: {s3_url}")
                    
                    # Send email synchronously using S3 URL
                    subject = 'Congratulations on Course Completion – Keep Moving Forward!'
                    body = f"Dear {c} \n\nCongratulations on successfully completing your course at Codegnan!\nWe're proud of the effort and commitment you've shown throughout your learning journey. \n\nAs you move ahead: \n-> Stay focused on your goals\n-> Keep practicing consistently\n-> Don't miss out applying for relevant jobs \n\nKeep us updated on your progress—we'd love to hear your success stories!\n\nWe'd also be grateful if you could spare a moment to share your experience by leaving a Google Review: \n\n https://g.co/kgs/SoHeUPK  \n\nWishing you continued success in your career. \n\nAll the best for what's next—keep pushing forward!"
                    
                    # Send email with S3 URL (with timeout protection)
                    try:
                        result_queue = queue.Queue()
                        
                        def email_worker():
                            try:
                                result = send_email_sync(i, subject, body, c.strip(), s3_url)
                                result_queue.put(('success', result))
                            except Exception as e:
                                result_queue.put(('error', str(e)))
                        
                        email_thread = threading.Thread(target=email_worker)
                        email_thread.daemon = True
                        email_thread.start()
                        # Adjust timeout based on batch size
                        timeout_seconds = 15 if total_records > 50 else 30
                        email_thread.join(timeout=timeout_seconds)
                        
                        if email_thread.is_alive():
                            email_status = 'Email timeout: Taking too long to send'
                            #print(f"PROD ERROR - Email timeout for {c.strip()}")
                        else:
                            try:
                                status, result = result_queue.get_nowait()
                                if status == 'success':
                                    email_status = result
                                else:
                                    email_status = f'Email failed: {result}'
                                    #print(f"PROD ERROR - Email failed for {c.strip()}: {result}")
                            except queue.Empty:
                                email_status = 'Email status unknown'
                    except Exception as email_error:
                        email_status = f'Email system error: {str(email_error)}'
                        #print(f"PROD ERROR - Email system error for {c.strip()}: {email_error}")
            
                # Validate if studentId and email already exist
                existing_cert = Certificates_collection.find_one({
                    '$or': [
                        {'certificates.studentID': j},
                        {'certificates.email': i}
                    ]
                })
                
                if existing_cert:
                    email_status = 'Already exists: Student ID or Email found in database'
                    s3_url = None
                    print(f"PROD INFO - Skipping {c.strip()}: Already exists in database")
                
                # Add to batch for MongoDB storage
                current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M")
                certificates_batch.append({
                    'studentID':j,
                    'name': c,
                    'email': i,
                    'status': email_status,
                    'certificate_url': s3_url,
                    'datetime': current_time
                })
                
            except Exception as e:
                name = c if 'c' in locals() else 'Unknown'
                print(f"PROD ERROR - Processing failed for {name}: {str(e)}")
                # Continue processing other certificates even if one fails
                certificates_batch.append({
                    'studentID': j if 'j' in locals() else 'Unknown',
                    'name': name,
                    'email': i if 'i' in locals() else 'Unknown',
                    'status': f'Processing Failed: {str(e)}',
                    'certificate_url': None,
                    'datetime': datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M")
                })
            
            count += 1
            
            # Save progress every 10 certificates for large batches
            if count % 10 == 0 and total_records > 20:
                try:
                    # Save intermediate progress to MongoDB
                    if certificates_batch:
                        existing_batch = Certificates_collection.find_one({'batch_no': batch_no})
                        if existing_batch:
                            Certificates_collection.update_one(
                                {'batch_no': batch_no},
                                {'$push': {'certificates': {'$each': certificates_batch[-10:]}}}
                            )
                        print(f"PROD DEBUG - Saved progress: {count}/{total_records} completed")
                except Exception as save_error:
                    print(f"PROD ERROR - Progress save failed: {str(save_error)}")
        
        # Store certificates - append to existing batch or create new one
        try:
            if certificates_batch:
                existing_batch = Certificates_collection.find_one({'batch_no': batch_no})
                
                if existing_batch:
                    # Append to existing batch
                    Certificates_collection.update_one(
                        {'batch_no': batch_no},
                        {
                            '$push': {'certificates': {'$each': certificates_batch}},
                            '$inc': {'total_certificates': len(certificates_batch)},
                            '$set': {'updated_at': datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M")}
                        }
                    )
                else:
                    # Create new batch
                    batch_document = {
                        'batch_no': batch_no,
                        'created_at': datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M"),
                        'total_certificates': len(certificates_batch),
                        'certificates': certificates_batch
                    }
                    Certificates_collection.insert_one(batch_document)
        except Exception as db_error:
            print(f"MongoDB batch storage error: {str(db_error)}")
        
        # Clean up temp files and memory
        if os.path.exists(excel_file_path):
            os.remove(excel_file_path)
        
        # Clean up certificate directory for large batches
        if total_records > 50 and os.path.exists(pdf_path):
            try:
                shutil.rmtree(pdf_path)
                #print(f"PROD DEBUG - Cleaned up {total_records} temporary PDF files")
            except Exception as cleanup_error:
                print(f"PROD ERROR - Cleanup failed: {str(cleanup_error)}")
        
        print(f"PROD DEBUG - Batch processing completed: {len(certificates_batch)} certificates processed")
        
            
    except Exception as e:
        print(f"Background processing error: {str(e)}")
    finally:
        pass  # No cleanup needed for PDF generator

class Certificates(Resource):
    def __init__(self):
        super().__init__()

    @manager_required
    def post(self):
        if 'file' not in request.files:
            return {"error": "No file selected"}, 400
        
        file = request.files['file']
        batchno = request.form.get('batchno')
        if not file or not batchno:
            return {"error": "Missing required fields: file or batch number"}, 400
        
        if file.filename == '':
            return {"error": "No file selected"}, 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(tempfile.gettempdir(), filename)
            file.save(filepath)

            try:
                # Validate Excel data first
                is_valid, validation_message = validate_excel_data(filepath)
                if not is_valid:
                    os.remove(filepath)  # Clean up temp file
                    return {"error": validation_message}, 400
                
                df = pd.read_excel(filepath)
                record_count = len(df)
                
                # Calculate estimated time based on batch size
                if record_count <= 10:
                    estimated_minutes = max(2, record_count * 0.5)
                elif record_count <= 50:
                    estimated_minutes = max(5, record_count * 0.3)
                else:
                    estimated_minutes = max(10, record_count * 0.2)  # Faster for large batches
                
                message = f"Processing {record_count} certificates in background. Generating personalized PDF certificates,Uploading to secure AWS S3 storage, Sending email notifications with attachments, Storing records in database"
                
                if record_count > 100:
                    message += f"Large batch detected - processing may take longer for {record_count} certificates."
                
                # Start background processing
                processing_thread = threading.Thread(
                    target=process_certificates_background,
                    args=(filepath, None, batchno)
                )
                processing_thread.daemon = True
                processing_thread.start()
                
                # Return immediate response
                return {
                    "message": message,
                    "processing_info": {
                        "total_records": record_count,
                        "estimated_minutes": int(estimated_minutes),
                        "status": "processing_started"
                    }
                }, 200
                
            except Exception as e:
                return {"error": f"Error processing file: {str(e)}"}, 500

    @manager_required        
    def get(self):
        batchno = request.args.get('batchno')

        if not batchno:
            return {"error": "Batch number is required"}, 400

        batch_data = Certificates_collection.find_one({'batch_no': batchno})
        if not batch_data:
            return {"error": "Batch not found"}, 404
        
        # Extract only name, email, status from certificates
        simplified_certificates = [
            {
                "studentID": cert["studentID"],
                "name": cert["name"],
                "email": cert["email"],
                "status": cert["status"]
            }
            for cert in batch_data.get("certificates", [])
        ]
        
        return simplified_certificates, 200