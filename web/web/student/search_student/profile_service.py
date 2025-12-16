import base64,os
from gridfs import GridFS
import boto3
from botocore.exceptions import ClientError

def init_s3_client(self):
    """Initialize S3 client"""
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

def get_from_s3(self, key):
    """Get file from S3"""
    if not hasattr(self, 's3_client') or not self.s3_client or not self.bucket_name:
        return None
    try:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()
    except ClientError as e:
        # Silently handle missing files - no logging for 404s
        return None

def profile_service(self, std_id):
    # Initialize S3 client if not already done
    if not hasattr(self, 's3_client'):
        init_s3_client(self)
    
    # STEP 1: Check S3 first
    try:
        for ext in ['jpg', 'png']:
            s3_key = f"profile_pics/{std_id}.{ext}"
            s3_data = get_from_s3(self, s3_key)
            if s3_data:
                # Found in S3 - return immediately, DON'T call MongoDB
                return base64.b64encode(s3_data).decode('utf-8')
    except Exception as e:
        pass  # Silent fail
    
    # STEP 2: S3 doesn't have it - NOW call MongoDB as fallback
    # try:
    #     self.fs = GridFS(self.db)
    #     pic = self.fs.find_one({'filename': std_id})
    #     if pic:
    #         return base64.b64encode(pic.read()).decode('utf-8')
    # except Exception as e:
    #     pass  # Silent fail
    
    # Not found anywhere
    return None   