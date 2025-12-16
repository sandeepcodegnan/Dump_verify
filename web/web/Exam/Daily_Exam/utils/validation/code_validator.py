"""Code validation utilities - Security (Language agnostic)"""
import re
from typing import List
from web.Exam.Daily_Exam.config.settings import SecurityConfig
from web.Exam.Daily_Exam.exceptions.exceptions import ValidationError

def validate_code_safety(code: str, language: str) -> List[str]:
    """Language-specific code safety validation"""
    if not code or not isinstance(code, str):
        return ["Invalid code input"]
    if not language or not isinstance(language, str):
        return ["Invalid language input"]
    
    warnings = []
    lang_lower = language.lower()
    
    patterns = SecurityConfig.DANGEROUS_PATTERNS.get(lang_lower, [])
    for pattern in patterns:
        if re.search(pattern, code, re.IGNORECASE):
            warnings.append(f"Potentially dangerous pattern: {pattern}")
    
    return warnings

def sanitize_code_input(code: str) -> str:
    """Security-focused code sanitization with length validation"""
    if not isinstance(code, str):
        raise ValidationError("Code must be string")
    
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', code)
    
    # Use normalize_newlines for consistent newline handling
    from web.Exam.Daily_Exam.utils.formatting.formatters import normalize_newlines
    sanitized = normalize_newlines(sanitized)
    
    # Security: Limit code length
    if len(sanitized) > SecurityConfig.MAX_CODE_LENGTH:
        raise ValidationError("Code too long")
    
    return sanitized