from flask import Flask,send_file,request,abort
from web.jwt.auth_middleware import student_required
from flask_restful import Resource
from web.db.db_utils import get_collection

def get_student_collection():
    return get_collection('students')
from io import BytesIO
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

class UpdateResume(Resource):
    def __init__(self) -> None:
        super().__init__()
        self.student_collection = get_student_collection()
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            self.bucket_name = os.getenv('S3_BUCKET_Students_Files', 'codegnan-students-files')
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
            self.s3_client = None
            self.bucket_name = None
    
    def upload_to_s3(self, file_data, key, content_type='application/pdf'):
        """Upload file to S3"""
        if not self.s3_client or not self.bucket_name:
            return None
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )
            return f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
        except ClientError as e:
            print(f"S3 upload failed: {e}")
            return None
    
    def delete_from_s3(self, key):
        """Delete file from S3"""
        if not self.s3_client or not self.bucket_name:
            return False
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"S3 delete failed: {e}")
            return False
    
    def get_from_s3(self, key):
        """Get file from S3"""
        if not self.s3_client or not self.bucket_name:
            return None
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            print(f"S3 get failed: {e}")
            return None

    @student_required
    def post(self):
        student_id = request.form["student_id"]
        resume_file = request.files.get('resume')
        pdf_content = resume_file.read()

        if not student_id:
            return {"error": "Missing required parameter: student_id"}, 400
        
        student_doc = self.student_collection.find_one({"id": student_id})
        
        if not student_doc:
            return {"message": "No student found", "student_id": student_id}, 404
        
        s3_key = f"resumes/{student_id}.pdf"
        
        # Delete old resume if exists
        if student_doc.get('resume_url'):
            self.delete_from_s3(s3_key)
        
        s3_url = self.upload_to_s3(pdf_content, s3_key)
        
        if s3_url:
            self.student_collection.update_one(
                {"id": student_id},
                {"$set": {"resume_url": s3_url}}
            )
            return {"message": "Resume uploaded to S3", "userType": "student", "student_id": student_id}, 200
        else:
            return {"message": "S3 upload failed", "student_id": student_id}, 500
            
    @student_required
    def get(self):
        student_id = request.args.get('resumeId')
        
        if not student_id:
            return {"error": "missing required fields"}, 404
        
        # Check student exists
        student_doc = self.student_collection.find_one({"id": student_id})
        if not student_doc:
            return {"error": "Student not found"}, 404
        
        # Check if student has resume_url
        if not student_doc.get('resume_url'):
            return {"error": "Resume not found"}, 404
        
        # Getting S3 data
        s3_key = f"resumes/{student_id}.pdf"
        s3_data = self.get_from_s3(s3_key)
        
        if s3_data:
            return send_file(
                BytesIO(s3_data),
                as_attachment=True,
                download_name=f"{student_id}.pdf",
                mimetype="application/pdf"
            )
        
        return {"error": "Resume not found"}, 404       