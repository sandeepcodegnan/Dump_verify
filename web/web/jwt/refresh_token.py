from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import decode_token, get_jwt_identity, get_jwt
from flask_jwt_extended.exceptions import JWTExtendedException
from .jwt_utils import JWTManager
from datetime import datetime
from web.related.logout import is_token_blacklisted

class RefreshToken(Resource):
    def post(self):
        """Handle refresh token request with proper validation"""
        try:
            # Get refresh token from request body
            refresh_token = request.json.get('refresh_token')
            if not refresh_token:
                return {
                    "message": "Missing refresh token in request body",
                    "error": "NO_REFRESH_TOKEN"
                }, 401
            
            # Decode and validate the refresh token
            try:
                decoded_token = decode_token(refresh_token)
                
                # Check if token is blacklisted
                token_jti = decoded_token.get('jti')
                if token_jti and is_token_blacklisted(token_jti):
                    return {
                        "message": "Refresh token has been revoked",
                        "error": "TOKEN_REVOKED"
                    }, 401
                
                # Check if token is refresh type
                if decoded_token.get('type') != 'refresh':
                    return {
                        "message": "Invalid token type. Expected refresh token",
                        "error": "INVALID_TOKEN_TYPE"
                    }, 401
                
                # Check if token is expired
                exp_timestamp = decoded_token.get('exp')
                if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
                    return {
                        "message": "Refresh token has expired",
                        "error": "TOKEN_EXPIRED"
                    }, 401
                
                # Extract user data from refresh token
                user_email = decoded_token.get('sub')
                
                # Create user data for new tokens (same structure as login)
                user_data = {
                    "email": user_email,
                    "userType": decoded_token.get("userType", ""),
                    "location": decoded_token.get("location", ""),
                    "id": decoded_token.get("id", ""),
                    "profile": decoded_token.get("profile")
                }
                
                # Generate new access and refresh tokens (same as login)
                new_access_token = JWTManager.generate_token(user_data)
                new_refresh_token = JWTManager.generate_refresh_token(user_data)
                
                return {
                    "message": "Login successful",
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "token_type": "Bearer"
                }, 200
                
            except JWTExtendedException as e:
                return {
                    "message": "Invalid or malformed refresh token",
                    "error": str(e)
                }, 401
            except Exception as e:
                return {
                    "message": "Failed to decode refresh token",
                    "error": str(e)
                }, 401
                
        except Exception as e:
            return {
                "message": "Failed to refresh token",
                "error": str(e)
            }, 401