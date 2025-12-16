from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request

# In-memory blacklist storage
blacklisted_tokens = set()

class Logout(Resource):
    def post(self):
        """Logout user"""
        try:
            verify_jwt_in_request(optional=False, fresh=False)
            token = get_jwt()
            jti = token['jti']
            blacklisted_tokens.add(jti)
        except Exception:
            # Token is expired or invalid, but still allow logout
            pass
        
        return {
            "message": "Logout successful",
            "status": "success"
        }, 200

def is_token_blacklisted(jti):
    """Check if token is blacklisted"""
    return jti in blacklisted_tokens