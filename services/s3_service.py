"""S3 service for image upload and management."""
import os
import uuid
import boto3
import streamlit as st
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

class S3Service:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
            self.s3_bucket = os.getenv("S3_BUCKET_QUESTION_IMAGES")
            
            if not all([os.getenv("AWS_ACCESS_KEY_ID"), os.getenv("AWS_SECRET_ACCESS_KEY"), 
                       os.getenv("AWS_REGION"), self.s3_bucket]):
                raise Exception("AWS S3 configuration incomplete")
                
        except Exception as e:
            st.error(f"S3 client initialization failed: {str(e)}")
            self.s3_client = None
    
    def upload_image(self, uploaded_file):
        """Upload image to S3 and return URL."""
        if not self.s3_client:
            return None
            
        try:
            # Generate secure filename
            file_extension = ".jpg"  # Default extension
            if uploaded_file.name:
                file_extension = "." + uploaded_file.name.split(".")[-1]
            
            key = f"cover-images/{uuid.uuid4()}{file_extension}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=uploaded_file.read(),
                ContentType=uploaded_file.type or "image/jpeg"
            )
            
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{key}"
            
        except Exception as e:
            st.error(f"S3 upload failed: {str(e)}")
            return None
    
    def delete_image(self, image_url):
        """Delete image from S3 using URL."""
        if not self.s3_client or not image_url:
            return False
            
        try:
            if self.s3_bucket in image_url:
                s3_key = image_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
                return True
        except Exception:
            pass
        return False