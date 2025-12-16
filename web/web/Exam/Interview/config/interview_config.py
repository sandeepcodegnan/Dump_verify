"""Interview Module Configuration"""
import os
from dotenv import load_dotenv
from web.Exam.exam_central_db import get_collection

# Load environment variables
load_dotenv()

class InterviewConfig:
    """Interview system configuration"""
    
    # External Interview API Configuration
    INTERVIEW_API_BASE_URL = os.getenv('INTERVIEW_API_BASE_URL')
    INTERVIEW_API_KEY = os.getenv('INTERVIEW_API_KEY')
    INTERVIEW_API_TIMEOUT = int(os.getenv('INTERVIEW_API_TIMEOUT', 30))
    
    # Interview Job Configuration
    INTERVIEW_JOB_TITLE_TEMPLATE = "{batch}-Week_{week_num}_interview"
    INTERVIEW_ENDPOINT = "/interview/py/jobs/codegnan"
    

    
    # API Headers Template
    @classmethod
    def get_api_headers(cls):
        return {
            "accept": "application/json",
            "X-API-Key": cls.INTERVIEW_API_KEY,
            "Content-Type": "application/json"
        }
    
    # Get assigned manager from database
    @classmethod
    def get_assigned_manager(cls, location):
        """Get manager assigned for interviews based on location"""
        try:
            manager_collection = get_collection('Manager')
            manager = manager_collection.find_one({
                'location': location.lower(),
                'show_in_report': 'True',
                'usertype': 'manager'
            })
            return manager['email'] if manager else 'saketh@codegnan.com'  # fallback
        except Exception:
            return 'sandeep@codegnan.com'  # fallback on error
    
    # Validation
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_configs = [
            ('INTERVIEW_API_BASE_URL', cls.INTERVIEW_API_BASE_URL),
            ('INTERVIEW_API_KEY', cls.INTERVIEW_API_KEY),
        ]
        
        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
        
        if missing_configs:
            raise ValueError(f"Missing required interview configurations: {', '.join(missing_configs)}")
        
        return True