import json
import os
from pymongo import MongoClient
from gridfs import GridFS
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

# Load configuration once
with open('local_config.json', 'r') as config_file:
    config = json.load(config_file)

# Database connection setup
mongo_url = os.getenv("DB_URL", config["MONGO_CONFIG"].get("url"))
db_name = os.getenv("DB_NAME", config["MONGO_CONFIG"].get("db_name", "codegnan_product"))
client = MongoClient(mongo_url, maxPoolSize=50, serverSelectionTimeoutMS=30000, socketTimeoutMS=10000)
db = client[db_name]

# GridFS setup
fs = GridFS(db)

# S3 setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)
bucket_name = os.getenv('S3_BUCKET_Students_Files', 'codegnan-students-files')

# Centralized collection references - all collections from all modules
collections = {
    # User collections
    'admin': db["Admin"],
    'bde': db["BDE_data"],
    'managers': db["Manager"],
    'mentors': db["Mentors"],
    'practice_mentors': db["Practice_Mentors"],
    'sales': db["Sales"],
    'testers': db["Testers"],
    'students': db["student_login_details"],
    'student_login_details': db["student_login_details"],
    
    # Job and placement collections
    'jobs': db["jobs_listing"],
    'jobs_listing': db["jobs_listing"],
    'bde_data': db["BDE_data"],
    
    # Batch and course collections
    'batches': db["Batches"],
    'curriculum': db["Curriculum"],
    'mentor_curriculum_table': db["Mentor_Curriculum_Table"],
    'schedule': db["Schedule"],
    
    # Attendance collections
    'attendance': db["Attendance"],
    'practice_attendance': db["Practice_Attendance"],
    
    # Exam collections
    'daily_exam': db["Daily-Exam"],
    'weekly_exam': db["Weekly-Exam"],
    'monthly_exam': db["Monthly-Exam"],
    'ats_check': db["ATScheck"],
    
    # Request collections
    'leave_request': db["Leave_Request"],
    
    # Configuration collections
    'locations': db["locations"],
    'tech_stack': db["Tech_stack"],
    'educational_branches': db["Educational_Branches"],
    'courses_skills': db["Courses-Skills"],
    
    # File storage collections
    'fs_files': db["fs.files"],
    'fs_chunks': db["fs.chunks"],
    
    # Other collections
    'otp': db["otp_verification"],
    'certificates': db["Certificates"]
}

def get_collection(name):
    """Get collection by name"""
    return collections.get(name)

def get_db():
    """Get database instance"""
    return db

def get_client():
    """Get MongoDB client instance"""
    return client

def get_gridfs():
    """Get GridFS instance"""
    return fs

def get_s3_client():
    """Get S3 client instance"""
    return s3_client

def get_s3_bucket_name():
    """Get S3 bucket name"""
    return bucket_name

def get_from_s3(key):
    """Get file from S3"""
    if not s3_client or not bucket_name:
        return None
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchKey':
            print(f"S3 get failed: {e}")
        return None

def get_mcq_collection(subject):
    """Get MCQ collection for a subject"""
    return db[f"{subject.lower()}_mcq"]

def get_code_collection(subject):
    """Get code collection for a subject"""
    return db[f"{subject.lower()}_code"]

def get_query_collection(subject):
    """Get query collection for a subject (for SQL subjects)"""
    return db[f"{subject.lower()}_query"]

def get_user_collections():
    """Get all user-related collections"""
    return {
        'admin': collections['admin'],
        'bde': collections['bde'],
        'managers': collections['managers'],
        'mentors': collections['mentors'],
        'students': collections['student_login_details'],
        'testers': collections['testers'],
        'practice_mentors': collections['practice_mentors'],
        'sales': collections['sales']
    }