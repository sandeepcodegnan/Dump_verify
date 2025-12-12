"""Authentication service for user management."""
import streamlit as st
from config.database import get_collection
from utils.constants import ROLES

class AuthService:
    def __init__(self):
        self.users_collection = get_collection("users")
    
    def authenticate(self, username, password):
        """Authenticate user credentials."""
        user = self.users_collection.find_one({"username": username})
        if user and user['password'] == password:
            return {"user_id": user["user_id"], "role": user["role"], "name": user["name"]}
        return None
    
    def has_permission(self, user_role, permission):
        """Check if user role has specific permission."""
        return permission in ROLES.get(user_role, [])
    
    def login_user(self, user_data):
        """Store user session data."""
        st.session_state.user = user_data
        st.session_state.authenticated = True
    
    def logout_user(self):
        """Clear user session."""
        if 'user' in st.session_state:
            del st.session_state.user
        if 'authenticated' in st.session_state:
            del st.session_state.authenticated
    
    def is_authenticated(self):
        """Check if user is authenticated."""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self):
        """Get current user data."""
        return st.session_state.get('user', None)
    
    def change_password(self, user_id, new_password):
        """Change user password."""
        try:
            result = self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"password": new_password}}
            )
            return result.modified_count > 0
        except:
            return False