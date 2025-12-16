"""
Testing Module Configuration
Centralized configuration following Parent_Reports pattern
"""
import os

# OneCompiler Configuration
ONECOMPILER_CONFIG = {
    "access_token": os.getenv("ONECOMPILER_ACCESS_TOKEN"),
    "api_url": os.getenv("ONECOMPILER_API_URL"),
    "timeout_code": 15,
    "timeout_sql": 30
}

# Security Configuration
SECURITY_CONFIG = {
    "default_tester_password": os.getenv("DEFAULT_TESTER_PASSWORD", "CG@Tester")
}

# Whitelist of allowed subjects for security
ALLOWED_SUBJECTS = {
    "python", "flask", "java", "advancedjava", "mysql", "dataanalytics", 
    "frontend", "reactjs", "nodejs", "expressjs", "mongodb", "devops", 
    "softskills", "aptitude", "statistics", "machinelearning", "deeplearning", 
    "dsa", "c"
}

# Language Extension Mapping
LANGUAGE_EXTENSIONS = {
    "python": "py", "python2": "py", "javascript": "js",
    "java": "java", "c": "c", "cpp": "cpp", "c++": "cpp",
    "ruby": "rb", "go": "go", "mysql": "sql", "sql": "sql"
}

# Question Types Configuration
QUESTION_TYPES = {
    "mcq_test": {
        "collection_suffix": "mcq_test",
        "required_fields": ["Question", "Options", "Correct_Option", "Score"],
        "auto_verify": False
    },
    "code_test": {
        "collection_suffix": "code_test", 
        "required_fields": ["Question", "Sample_Input", "Sample_Output", "Hidden_Test_Cases"],
        "auto_verify": True
    },
    "code_codeplayground_test": {
        "collection_suffix": "code_codeplayground_test",
        "required_fields": ["Question", "Sample_Input", "Sample_Output", "Hidden_Test_Cases"],
        "auto_verify": True
    },
    "query_test": {
        "collection_suffix": "query_test",
        "required_fields": ["Question", "Input", "Expected_Output"],
        "auto_verify": True
    },
    "query_codeplayground_test": {
        "collection_suffix": "query_codeplayground_test",
        "required_fields": ["Question", "Input", "Expected_Output"],
        "auto_verify": True
    }
}

# Subject-based question type mapping
SUBJECT_QUESTION_TYPES = {
    "python": ["mcq", "code", "code_codeplayground"],
    "java": ["mcq", "code", "code_codeplayground"],
    "mysql": ["mcq", "query", "query_codeplayground"],
    "c": ["mcq", "code", "code_codeplayground"],
    "cpp": ["mcq", "code", "code_codeplayground"],
    "dataanalytics": ["mcq"],
    "statistics": ["mcq"],
    "machinelearning": ["mcq"],
    "deeplearning": ["mcq"],
    "aptitude": ["mcq"]
}



def get_collection_name(subject: str, question_type: str) -> str:
    """Generate collection name for subject and question type"""
    if question_type not in QUESTION_TYPES:
        raise ValueError(f"Invalid question type: {question_type}")
    
    suffix = QUESTION_TYPES[question_type]["collection_suffix"]
    return f"{subject.lower()}_{suffix}"

def validate_question_type(question_type: str) -> bool:
    """Validate if question type is supported"""
    return question_type in QUESTION_TYPES

def get_required_fields(question_type: str) -> list:
    """Get required fields for question type"""
    if question_type not in QUESTION_TYPES:
        return []
    return QUESTION_TYPES[question_type]["required_fields"]

def get_subject_question_types(subject: str) -> list:
    """Get allowed question types for a subject"""
    return SUBJECT_QUESTION_TYPES.get(subject.lower(), ["mcq"])