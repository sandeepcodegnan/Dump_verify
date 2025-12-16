"""Configuration settings - Configuration Layer (Environment Separated)"""
import os
from typing import Dict, Set

def safe_int_env(key: str, default: str) -> int:
    """Safely convert environment variable to int"""
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return int(default)

def safe_float_env(key: str, default: str) -> float:
    """Safely convert environment variable to float"""
    try:
        return float(os.getenv(key, default))
    except ValueError:
        return float(default)

# Exam Types (Business Configuration)
ALLOWED_EXAM_TYPES: Set[str] = {"Daily-Exam", "Weekly-Exam", "Monthly-Exam"}

# Exam Time Constraints (Business Configuration)
EXAM_TIME_CONSTRAINTS: Dict[str, int] = {
    "Daily-Exam": 30,  # Maximum 30 minutes
    "Weekly-Exam": 60,  # Maximum 2 hours
    "Monthly-Exam": 120  # Maximum 3 hours
}

# Exam Day Restrictions (Business Configuration)
WEEKDAY_ONLY_EXAMS: Set[str] = {"Daily-Exam"}  # Only weekdays allowed

# Subject Types (Business Configuration)
SQL_SUBJECTS: Set[str] = {"mysql", "sql"}
NON_TECH_SUBJECTS: Set[str] = {"aptitude", "softskills"}
EXCLUDED_EXAM_SUBJECTS: Set[str] = {"softskills"}

# Subject-based question type mapping
SUBJECT_QUESTION_TYPES: Dict[str, list] = {
    "python": ["mcq", "code"],
    "java": ["mcq", "code"],
    "javascript": ["mcq", "code"],
    "c": ["mcq", "code"],
    "cpp": ["mcq", "code"],
    "mysql": ["mcq", "query"],
    "sql": ["mcq", "query"],
    "dataanalytics": ["mcq"],
    "statistics": ["mcq"],
    "machinelearning": ["mcq"],
    "deeplearning": ["mcq"],
    "aptitude": ["mcq"],
    "softskills": ["mcq"]
}

# Scoring Configuration
DEFAULT_MCQ_SCORE = 1
DIFFICULTY_SCORES = {"easy": 5, "medium": 10, "hard": 15}
DEFAULT_DIFFICULTY_SCORE = 5

# Exam Toggle Configuration
DEFAULT_EXAM_TOGGLE_STATE = False  # Disabled by default for safety

# External Service Configuration
class ExternalServiceConfig:
    ONECOMPILER_API_URL = os.getenv("ONECOMPILER_API_URL")
    ONECOMPILER_ACCESS_TOKEN = os.getenv("ONECOMPILER_ACCESS_TOKEN")
    ONECOMPILER_TIMEOUT = safe_int_env("ONECOMPILER_TIMEOUT", "15")

# Cache Configuration
class CacheConfig:
    SUBMISSION_CACHE_TTL = safe_int_env("SUBMISSION_CACHE_TTL", "3600")  # 1 hour

# Security Configuration
class SecurityConfig:
    MAX_CODE_LENGTH = safe_int_env("MAX_CODE_LENGTH", "50000")  # 50KB
    
    # Language-specific dangerous patterns - single source of truth
    DANGEROUS_PATTERNS = {
        "python": [
            r'import\s+os', r'import\s+subprocess', r'import\s+sys',
            r'__import__', r'eval\s*\(', r'exec\s*\(',
            r'open\s*\(', r'file\s*\(', r'input\s*\(',
            r'raw_input\s*\(', r'compile\s*\('
        ],
        "javascript": [
            r'require\s*\(', r'process\s*\.', r'fs\s*\.',
            r'eval\s*\(', r'Function\s*\(', r'setTimeout\s*\(',
            r'setInterval\s*\('
        ],
        "java": [
            r'Runtime\s*\.', r'ProcessBuilder', r'System\s*\.',
            r'File\s*\(', r'FileInputStream', r'FileOutputStream'
        ]
    }

# WhatsApp Configuration
class WhatsAppConfig:
    MAX_WORKERS = safe_int_env("WHATSAPP_MAX_WORKERS", "5")
    RATE_LIMIT_SECONDS = safe_float_env("WHATSAPP_RATE_LIMIT_SECONDS", "2.0")

# Language Configuration
class LanguageConfig:
    EXTENSIONS: Dict[str, str] = {
        "python": "py", "python2": "py", "python3": "py",
        "javascript": "js", "node": "js",
        "java": "java", "c": "c", "c++": "cpp", "cpp": "cpp",
        "ruby": "rb", "go": "go",
        "MySQL": "sql", "sql": "sql"
    }