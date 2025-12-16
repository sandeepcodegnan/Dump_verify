import boto3
import os
import json
import botocore.config
import botocore.exceptions as bex

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET = os.getenv("S3_BUCKET_MYSQL_TEMPLATES", "codegnan-mysql-templates")

_cfg = botocore.config.Config(
    max_pool_connections=50,
    connect_timeout=10,
    read_timeout=60,
    retries={"max_attempts": 3, "mode": "adaptive"},
    tcp_keepalive=True,
)

# Module-level S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=REGION,
    config=_cfg,
)

def ensure_bucket_exists(bucket_name: str) -> None:
    """Create bucket if it doesn't exist"""
    try:
        s3.head_bucket(Bucket=bucket_name)
    except bex.ClientError as e:
        if e.response['Error']['Code'] in ("404", "NoSuchBucket"):
            create_args = {"Bucket": bucket_name}
            if REGION != "us-east-1":
                create_args['CreateBucketConfiguration'] = {'LocationConstraint': REGION}
            s3.create_bucket(**create_args)
            print(f"Created bucket {bucket_name}")
        else:
            raise

class S3Utils:
    def __init__(self):
        self.bucket_name = BUCKET
        ensure_bucket_exists(self.bucket_name)
    
    def upload_file(self, file_obj, s3_key):
        """Upload file to S3"""
        try:
            s3.upload_fileobj(
                file_obj, 
                self.bucket_name, 
                s3_key,
                ExtraArgs={'ContentType': self._get_content_type(s3_key)}
            )
            return f"s3://{self.bucket_name}/{s3_key}"
        except bex.ClientError as e:
            raise Exception(f"S3 upload failed: {e}")
    
    def upload_sql_content(self, template_name, sql_content):
        """Upload SQL content to S3 - DRY principle"""
        from io import BytesIO
        sql_key = f"{template_name}/complete.sql"
        sql_buffer = BytesIO(sql_content.encode('utf-8'))
        return self.upload_file(sql_buffer, sql_key)
    
    def get_file_content(self, s3_key):
        """Get file content from S3"""
        try:
            response = s3.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read().decode('utf-8')
        except bex.ClientError as e:
            raise Exception(f"S3 download failed: {e}")
    
    def _get_content_type(self, filename):
        """Get content type based on file extension"""
        if filename.endswith('.sql'):
            return 'text/plain'
        elif filename.endswith('.json'):
            return 'application/json'
        return 'application/octet-stream'