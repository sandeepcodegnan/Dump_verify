"""Custom exceptions - SoC principle"""

class DailyExamError(Exception):
    """Base exception for Daily Exam module"""
    pass

class ValidationError(DailyExamError):
    """Input validation error"""
    pass

class ExamNotFoundError(DailyExamError):
    """Exam not found error"""
    pass

class ExamAlreadyStartedError(DailyExamError):
    """Exam already started error"""
    pass

class ExamAlreadySubmittedError(DailyExamError):
    """Exam already submitted error"""
    pass