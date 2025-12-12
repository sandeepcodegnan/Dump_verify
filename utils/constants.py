"""Application constants and configurations."""

# Subject codes for Q_id generation (MCQ collections)
SUBJECTS = {
    "PY": "python", "MY": "mysql", "JV": "java", "JS": "javascript",
    "RJ": "react", "NJ": "nodejs", "MG": "mongodb", "FL": "flask",
    "ML": "machinelearning", "DL": "deeplearning", "DS": "dsa",
    "DV": "devops", "AP": "aptitude", "SS": "softskills"
}

# Question types (MCQ only)
TYPES = {"M": "mcq"}

# Role-based permissions
ROLES = {
    "admin": ["allocate", "audit", "manage", "export", "analytics"],
    "intern": ["verify", "modify", "view_assigned", "bulk_verify"]
}

# Cache configuration
CACHE_CONFIG = {
    "questions_ttl": 300,
    "user_data_ttl": 1800,
    "metrics_ttl": 60
}

# Pagination settings
PAGINATION = {
    "default_page_size": 50,
    "max_page_size": 100
}