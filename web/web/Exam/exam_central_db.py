import json
import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from the main .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Get MongoDB configuration from environment variables
MONGO_CONFIG = os.getenv('DB_URL')
DB_NAME = os.getenv('DB_NAME', 'codegnan_product')
if not MONGO_CONFIG:
    # Fallback to local config file
    root_dir = Path(__file__).resolve().parent.parent.parent
    config_path = os.path.join(root_dir, 'local_config.json')
    try:
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)
        MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
    except FileNotFoundError:
        raise Exception("Neither DB_URL environment variable nor local_config.json found")

# MongoDB connection configuration
MONGO_CLIENT_CONFIG = {
    'maxPoolSize': 100,
    'minPoolSize': 20,
    'connectTimeoutMS': 10000,
    'serverSelectionTimeoutMS': 10000,
    'waitQueueTimeoutMS': 10000,
    'socketTimeoutMS': 60000,
    'retryWrites': True,
    'retryReads': True,
    'w': 1
}

def get_mongo_client():
    """Get a MongoDB client with connection pooling."""
    return MongoClient(MONGO_CONFIG, **MONGO_CLIENT_CONFIG)
    
    
# Get client and database - use a single client for the main process
client = get_mongo_client()
db = client[DB_NAME]

def get_db():
    """Get MongoDB database with proper connection pooling."""
    return get_mongo_client()[DB_NAME]

def init_worker():
    """Initialize worker process with MongoDB connection."""
    _ = get_db()

def get_collection(name):
    """Get collection from database."""
    return db[name]

# Collection definitions
COLLECTIONS = {
    # Core collections
    'student_collection': 'student_login_details',
    'daily_exam_collection': 'Daily-Exam',
    'weekly_exam_collection': 'Weekly-Exam', 
    'monthly_exam_collection': 'Monthly-Exam',
    'curriculum_collection': 'Mentor_Curriculum_Table',
    'batches_collection': 'Batches',
    'attendance_collection': 'Attendance',
    'practice_attendance_collection': 'Practice_Attendance',
    # WhatsApp collections
    'whatsapp_stats_collection': 'whatsapp_stats',
    # Testing collections
    'intern_verified_questions_collection': 'InternVerifiedQuestions',
    'interns_dumped_collection': 'internsdumped', 
    'testers_collection': 'Testers',
    'testers_curriculum_collection': 'Curriculum',
    # Parent report collections
    'parent_report_collection': 'parent_whatapp_report',
    'parent_report_status_collection': 'parent_report_status',
    'parent_message_status_collection': 'parent_message_status',
    # Other collections
    'codeplayground_collection': 'codeplayground',
    'feature_flags_collection': 'feature_flags',
    'location_flags_collection': 'feature_flags_location',
    'batch_flags_collection': 'feature_flags_batch',
    # Templates and configurations
    'mysql_templates_collection': 'mysql_templates',
    # window configurations
    'window_configs_collection': 'window_configs',
    'exam_toggle_collection': 'exam_toggles',
    # WhatsApp Admin Notifications
    'admin_notifications_collection': 'whatsapp_admin_notifications',
    'daily_report_status_collection': 'whatsapp_daily_report_status',
    # Manager collection
    'manager_collection': 'Manager',
    # Interviews collection
    'interviews_collection': 'interviews'
}

# Create collection objects
for var_name, collection_name in COLLECTIONS.items():
    globals()[var_name] = get_collection(collection_name)