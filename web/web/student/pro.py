from flask import Flask, send_file, request,abort,jsonify,make_response
from flask_restful import Resource
from web.jwt.auth_middleware import AllResource
from web.db.db_utils import get_collection

def get_student_collection():
    return get_collection('students')
from PIL import Image
import io
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

def compress_image(image_bytes, target_size_kb=10):
    """
    Compress the input image bytes so that its size is approximately at most target_size_kb (in KB).
    The function uses Pillow to open, convert, and (if needed) resize the image.
    Returns the compressed image bytes.
    """
    # Open the image from bytes
    image_io = io.BytesIO(image_bytes)
    try:
        image = Image.open(image_io)
    except Exception as e:
        raise ValueError("Invalid image file provided.")
   
    # Convert to RGB if necessary (JPEG requires RGB)
    if image.mode != "RGB":
        image = image.convert("RGB")
   
    quality = 85  # Starting quality setting
    compressed_io = io.BytesIO()
    image.save(compressed_io, format="JPEG", quality=quality)
    size_kb = len(compressed_io.getvalue()) / 1024

    # First, reduce quality until the size is under target_size_kb or quality reaches a threshold.
    while size_kb > target_size_kb and quality > 10:
        quality -= 5
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024

    # If quality reduction alone is insufficient, resize the image.
    if size_kb > target_size_kb:
        width, height = image.size
        # Calculate a scaling factor based on current size versus target size.
        factor = (target_size_kb / size_kb) ** 0.5 
        new_width = max(1, int(width * factor))
        new_height = max(1, int(height * factor))
        image = image.resize((new_width, new_height), Image.LANCZOS) 
        quality = 85  # Reset quality after resizing
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024
       
        # Further reduce quality if needed.
        while size_kb > target_size_kb and quality > 10:
            quality -= 5
            compressed_io = io.BytesIO()
            image.save(compressed_io, format="JPEG", quality=quality)
            size_kb = len(compressed_io.getvalue()) / 1024

    compressed_io.seek(0)
    return compressed_io.getvalue()

class Profile_pic(AllResource):
    def __init__(self):
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

    def upload_to_s3(self, file_data, key, content_type='image/png'):
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

    def get_from_s3(self, key):
        """Get file from S3"""
        if not self.s3_client or not self.bucket_name:
            return None
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                print(f"S3 get failed: {e}")
            return None

    def get(self):
        ids = request.args.get('student_id') 

        if not ids :
            return {"error":"missing required fields"},404
        
        # Check if student exists and has profile_url
        student = self.student_collection.find_one({"studentId": ids})
        if not student or not student.get('profile_url'):
            return {"error": "profile not found for this student id"}, 404
        
        # Check for files with common extensions
        for ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp']:
            s3_key = f"profile_pics/{ids}.{ext}"
            s3_data = self.get_from_s3(s3_key)
            if s3_data:
                pic_file = f"{ids}.{ext}"
                response = make_response(s3_data)
                response.headers.set('Content-Type', 'application/octet-stream')
                response.headers.set('Content-Disposition', f'attachment; filename="{pic_file}"')
                return response
        
        return {"error": "profile not found for this student id"}, 404       
    
    def post(self):
        std_id = request.form.get('studentId')
        profile = request.files.get('profilePic')
        profile_bytes = profile.read()
        
        # Get original file extension
        original_ext = profile.filename.split('.')[-1].lower() if profile.filename and '.' in profile.filename else 'jpg'
        
        try:
            pro_file = compress_image(profile_bytes, target_size_kb=10)
        except Exception as e:
            print(e)
            return {"error": "Failed to compress profile image: " + str(e)}, 400

        # Check if student exists and has existing S3 profile
        student = self.student_collection.find_one({"studentId": std_id})
        if student and student.get('profile_url'):
            # Extract key from existing S3 URL and delete
            existing_url = student['profile_url']
            if 's3.amazonaws.com/' in existing_url:
                existing_key = existing_url.split('s3.amazonaws.com/')[-1]
                self.delete_from_s3(existing_key)
        
        # Delete any existing files with common extensions
        for ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp']:
            self.delete_from_s3(f"profile_pics/{std_id}.{ext}")
        
        # Upload new file to S3
        s3_key = f"profile_pics/{std_id}.{original_ext}"
        s3_url = self.upload_to_s3(pro_file, s3_key)
        
        if s3_url:
            self.student_collection.update_one(
                {"studentId": std_id},
                {"$set": {"profile_url": s3_url}}
            )
            return {"message": "Student profile_pic updated successfully"}, 200
        else:
            return {"error": "Failed to upload profile picture"}, 500