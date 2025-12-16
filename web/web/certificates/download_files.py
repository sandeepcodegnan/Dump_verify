from flask_restful import Resource
from flask import request, send_file
import zipfile
import os
import boto3
import botocore.exceptions as bex
from io import BytesIO
import tempfile
from web.jwt.auth_middleware import manager_required
from web.db.db_utils import get_collection

Certificates_collection = get_collection('certificates')

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_certificates", "cg-course-completion-certificates")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

def download_from_s3(bucket_name, s3_key):
    try:
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        return response['Body'].read()
    except bex.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise

def list_s3_objects(bucket_name, prefix=""):
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', [])]
    except bex.ClientError:
        return []

class Dowload_certificates(Resource):

    @manager_required
    def get(self):
        
        batchno = request.args.get('batchno')

        if not batchno:
            return {"error": "Batch number is required"}, 400

        batch_data = Certificates_collection.find_one({'batch_no': batchno})
        if not batch_data:
            return {"error": "Batch not found"}, 404
        
        certificates = batch_data.get('certificates', [])
        if not certificates:
            return {"error": "No certificates found for this batch"}, 404
        
        # Get bucket name from latest batch entry, fallback to default
        bucket_name = batch_data.get('bucket_name', S3_BUCKET_NAME)
        
        # Get certificate filenames from database
        db_cert_files = {f"{cert.get('name').strip()}.pdf" for cert in certificates if cert.get('name')}
        
        # List available files in S3 bucket
        s3_prefix = f"certificates/{batchno}/"
        s3_files = list_s3_objects(bucket_name, s3_prefix)
        s3_cert_files = {os.path.basename(f) for f in s3_files if f.endswith('.pdf')}
        
        # Find matching files
        matching_files = db_cert_files.intersection(s3_cert_files)
        
        if not matching_files:
            return {"error": "No matching certificate files found"}, 404
        
        # Create zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_file in matching_files:
                s3_key = f"certificates/{batchno}/{pdf_file}"
                pdf_content = download_from_s3(bucket_name, s3_key)
                if pdf_content:
                    zipf.writestr(pdf_file, pdf_content)
        
        zip_buffer.seek(0)
        
        # Create temporary file for sending
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            temp_file.write(zip_buffer.getvalue())
            temp_file_path = temp_file.name
        
        return send_file(temp_file_path, as_attachment=True, download_name=f'certificates_{batchno}.zip')