"""
API Response Helper - DRY Principle
Standardizes all API responses
"""

class APIResponse:
    @staticmethod
    def success(data, status_code=200):
        """Standard success response"""
        return {"success": True, **data}, status_code
    
    @staticmethod
    def error(message, status_code=400):
        """Standard error response"""
        return {"success": False, "message": message}, status_code
    
    @staticmethod
    def not_found(message="Resource not found"):
        """Standard 404 response"""
        return APIResponse.error(message, 404)
    
    @staticmethod
    def server_error(message="Internal server error"):
        """Standard 500 response"""
        return APIResponse.error(message, 500)