from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from datetime import timedelta
import os
import uuid

class JWTManager:
    @staticmethod
    def generate_token(user_data, expires_delta=None):
        """Generate JWT access token for user"""
        if expires_delta is None:
            # Get expiration from env or default to 15 minutes
            minuts = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES',60))
            expires_delta = timedelta(minutes=minuts)
        
        additional_claims = {
            "id": user_data.get("id"),
            "location": user_data.get("location"),
            "email": user_data.get("email"),
            "profile": user_data.get("profile"),
            "userType": user_data.get("userType") 
        }
        
        return create_access_token(
            identity=user_data.get("email"),
            expires_delta=expires_delta,
            additional_claims=additional_claims,
            fresh=False
        )
    
    @staticmethod
    def generate_refresh_token(user_data):
        """Generate JWT refresh token for user"""
        days = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS',7))
        expires_delta = timedelta(days=days)
        
        additional_claims = {
            "id": user_data.get("id"),
            "location": user_data.get("location"),
            "email": user_data.get("email"),
            "profile": user_data.get("profile"),
            "userType": user_data.get("userType")
        }
        
        return create_refresh_token(
            identity=user_data.get("email"),
            expires_delta=expires_delta,
            additional_claims=additional_claims
        )
    
    @staticmethod
    def get_current_user():
        """Get current user from JWT token"""
        return get_jwt_identity()
    
    @staticmethod
    def get_user_claims():
        """Get additional claims from JWT token"""
        return get_jwt()
    
    @staticmethod
    def verify_token():
        """Verify JWT token and return user data or error"""
        try:
            verify_jwt_in_request()
            return {
                "valid": True,
                "user": get_jwt_identity(),
                "claims": get_jwt()
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }