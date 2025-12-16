from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_restful import Resource
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# Import blacklist checker
from web.related.logout import is_token_blacklisted

def token_required(f):
    """Decorator to require JWT token for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            # Check if token is blacklisted
            token = get_jwt()
            if is_token_blacklisted(token['jti']):
                return {"message": "Token has been invalidated", "error": "TOKEN_BLACKLISTED"}, 401
            return f(*args, **kwargs)
        except NoAuthorizationError:
            return {"message": "Missing Authorization Header", "error": "NO_AUTH_HEADER"}, 401
        except ExpiredSignatureError:
            return {"message": "Token has expired", "error": "TOKEN_EXPIRED"}, 401
        except InvalidTokenError:
            return {"message": "Invalid token", "error": "INVALID_TOKEN"}, 401
        except Exception as e:
            return {"message": "Unauthorized access", "error": "UNAUTHORIZED"}, 401
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to require specific roles for API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_type = claims.get("userType")
                
                if user_type not in allowed_roles:
                    return {"message": f"Access denied. Required roles: {', '.join(allowed_roles)}", "error": "INSUFFICIENT_PERMISSIONS"}, 403
                
                return f(*args, **kwargs)
            except NoAuthorizationError:
                return {"message": "Missing Authorization Header", "error": "NO_AUTH_HEADER"}, 401
            except ExpiredSignatureError:
                return {"message": "Token has expired", "error": "TOKEN_EXPIRED"}, 401
            except InvalidTokenError:
                return {"message": "Invalid token", "error": "INVALID_TOKEN"}, 401
            except Exception as e:
                return {"message": "Unauthorized access", "error": "UNAUTHORIZED"}, 401
        return decorated_function
    return decorator

# Role-specific decorators
def student_required(f):
    """Decorator for student-only endpoints"""
    return role_required("student_login_details")(f)

def mentor_required(f):
    """Decorator for mentor-only endpoints"""
    return role_required("Mentors","Practice_Mentors")(f)

def manager_required(f):
    """Decorator for manager-only endpoints"""
    return role_required("Manager","superManager")(f)

def bde_required(f):
    """Decorator for BDE-only endpoints"""
    return role_required("BDE_data")(f)

def admin_required(f):
    """Decorator for admin-only endpoints"""
    return role_required("Admin")(f)

def tester_required(f):
    """Decorator for tester-only endpoints"""
    return role_required("Testers")(f)

def manager_student(f):
    """Decorator for manager & student endpoints"""
    return role_required("Manager","student_login_details")(f)

def serstd_required(f):
    """Decorator for mentor@Manager endpoints"""
    return role_required("Mentors","Manager","Practice_Mentors")(f)

def exams_required(f):
    return role_required("superAdmin","Manager","Admin","Mentors")(f)

def multi_ABJP_required(f):
    return role_required("superManager","BDE_data","Admin", "Java", "Python")(f)

def all_mangers_required(f):
    """Decorator for staff (admins & BDE & mangers) endpoints"""
    return role_required("superAdmin","Manager","Admin","BDE_data")(f)

def multiple_required(f):
    """Decorator for staff (Both admins & mangers) endpoints"""
    return role_required("superAdmin","Manager","Admin", "Java", "Python","superManager","Sales")(f)

def multi_admins_required(f):
    """Decorator for staff ( /admins only) endpoints"""
    return role_required("superAdmin","Admin","Java","Python")(f)

def All_required(f):
    """Decorator for all endpoints"""
    return role_required("superAdmin","Manager","Admin", "BDE_data","Java", "Python","superManager","Sales")(f)

def leaderbd_required(f):
    """Decorator for all endpoints"""
    return role_required("superAdmin","Manager","Admin", "Mentors","Practice_Mentors","student_login_details")(f)

def skil_required(f):
    """Decorator for staff (admins & BDE & mangers) endpoints"""
    return role_required("BDE_data","student_login_details")(f)

def all_user_required(f):
    """Decorator for all endpoints"""
    return role_required("Manager","BDE_data", "Mentors","Practice_Mentors","student_login_details","Testers")(f)

def all_location(f):
    """Decorator for all endpoints"""
    return role_required("superAdmin","Admin","Java","Python","Manager","BDE_data","superManager","Sales")(f)

def Hierarchical_Feature_View(f):
    return role_required("superAdmin","Manager","Admin")(f)

def all_access_required(f):
    """Decorator for all roles access"""
    return role_required("student_login_details","Mentors","Practice_Mentors","Manager","superManager","BDE_data","Admin","superAdmin","Testers","Java","Python","Sales")(f)

class ProtectedResource(Resource):
    """Base class for protected resources that require JWT authentication"""
    method_decorators = [jwt_required()]
    
    def dispatch_request(self, *args, **kwargs):
        """Override to handle JWT errors properly"""
        try:
            # Verify JWT first before getting token
            verify_jwt_in_request()
            # Check if token is blacklisted
            token = get_jwt()
            if is_token_blacklisted(token['jti']):
                return {"message": "Token has been invalidated", "error": "TOKEN_BLACKLISTED"}, 401
            return super().dispatch_request(*args, **kwargs)
        except NoAuthorizationError:
            return {"message": "Missing Authorization Header", "error": "NO_AUTH_HEADER"}, 401
        except ExpiredSignatureError:
            return {"message": "Token has expired", "error": "TOKEN_EXPIRED"}, 401
        except InvalidTokenError:
            return {"message": "Invalid token", "error": "INVALID_TOKEN"}, 401
        except Exception as e:
            if "token" in str(e).lower():
                return {"message": "Unauthorized access", "error": "UNAUTHORIZED"}, 401
            raise e
    
    def get_current_user_email(self):
        """Get current user email from JWT token"""
        return get_jwt_identity()
    
    def get_current_user_data(self):
        """Get current user data from JWT token"""
        claims = get_jwt()
        return {
            "email": get_jwt_identity(),
            "userType": claims.get("userType"),
            "location": claims.get("location"),
            "id": claims.get("id")
        }
    
    def check_role(self, *allowed_roles):
        """Check if current user has required role"""
        claims = get_jwt()
        user_type = claims.get("userType")
        return user_type in allowed_roles
    
    def require_role(self, *allowed_roles):
        """Require specific role or return error"""
        if not self.check_role(*allowed_roles):
            return {"message": f"Access denied. Required roles: {', '.join(allowed_roles)}", "error": "INSUFFICIENT_PERMISSIONS"}, 403
        return None

class StudentResource(ProtectedResource):
    """Base class for student-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("student_login_details")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class MentorResource(ProtectedResource):
    """Base class for mentor-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("Mentors")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class ManagerResource(ProtectedResource):
    """Base class for manager-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("Manager")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class BDEResource(ProtectedResource):
    """Base class for BDE-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("BDE_data")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class AdminResource(ProtectedResource):
    """Base class for admin-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("Admin")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class TesterResource(ProtectedResource):
    """Base class for tester-only resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("Testers")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)

class AllResource(ProtectedResource):
    """Base class for staff (mentor, manager, BDE, admin, tester) resources"""
    def dispatch_request(self, *args, **kwargs):
        try:
            verify_jwt_in_request()
            role_check = self.require_role("student_login_details","Mentors", "Manager", "BDE_data", "Admin","superAdmin")
            if role_check:
                return role_check
            return super().dispatch_request(*args, **kwargs)
        except Exception as e:
            return super().dispatch_request(*args, **kwargs)