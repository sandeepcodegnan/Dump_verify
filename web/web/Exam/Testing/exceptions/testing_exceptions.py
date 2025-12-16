"""
Testing Module Custom Exceptions
Centralized error handling following Parent_Reports pattern
"""

class TestingBaseException(Exception):
    """Base exception for Testing module"""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ValidationError(TestingBaseException):
    """Validation related errors"""
    pass

class QuestionNotFoundError(TestingBaseException):
    """Question not found errors"""
    def __init__(self, message: str = "Question not found"):
        super().__init__(message, 404)

class ExecutionError(TestingBaseException):
    """Code/SQL execution errors"""
    def __init__(self, message: str = "Execution failed"):
        super().__init__(message, 500)

class VerificationError(TestingBaseException):
    """Verification process errors"""
    pass

class DatabaseError(TestingBaseException):
    """Database operation errors"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, 500)

class ErrorHandler:
    """Centralized error handling utility"""
    
    @staticmethod
    def handle_error(error: Exception) -> tuple:
        """Convert exceptions to standardized API responses"""
        if isinstance(error, TestingBaseException):
            return {"success": False, "message": error.message}, error.code
        
        # Handle standard exceptions
        if isinstance(error, ValueError):
            return {"success": False, "message": str(error)}, 400
        
        # Generic error handling
        return {"success": False, "message": "Internal server error"}, 500
    
    @staticmethod
    def create_success_response(data: dict, message: str = "Success") -> tuple:
        """Create standardized success response"""
        response = {"success": True, "message": message}
        response.update(data)
        return response, 200