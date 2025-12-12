"""Main entry point for Question Bank Verification System."""
import streamlit as st
from services.auth_service import AuthService

# Page configuration
st.set_page_config(
    page_title="Question Bank Verification System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for compact responsive theme
st.markdown("""
<style>
    /* Remove default padding and margins */
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    
    /* Reduce header sizes */
    h1 {
        font-size: 1.8rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0rem !important;
    }
    
    h2 {
        font-size: 1.4rem !important;
        margin-bottom: 0.3rem !important;
        margin-top: 0.5rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
        margin-bottom: 0.3rem !important;
        margin-top: 0.3rem !important;
    }
    
    /* Login header styling */
    .main-header {
        background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
        padding: 0.8rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .main-header h1 {
        font-size: 1.6rem !important;
        margin: 0 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.4rem 0.8rem;
        font-weight: 500;
        font-size: 0.9rem;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #1d4ed8;
    }
    
    /* Compact metrics */
    .metric-container {
        background: #f8fafc;
        padding: 0.5rem;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
    }
    
    /* Remove extra spacing */
    .element-container {
        margin-bottom: 0.3rem;
    }
    
    /* Compact tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        h1 {
            font-size: 1.4rem !important;
        }
        .main-header h1 {
            font-size: 1.3rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point."""
    auth_service = AuthService()
    
    # Check authentication
    if not auth_service.is_authenticated():
        show_login_page(auth_service)
    else:
        show_main_app(auth_service)

def show_login_page(auth_service):
    """Display login interface."""
    st.markdown('<div class="main-header"><h1>📚 Question Bank Verification System</h1></div>', 
                unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login")
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit and username and password:
                user_data = auth_service.authenticate(username, password)
                if user_data:
                    auth_service.login_user(user_data)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            elif submit:
                st.warning("Please enter username and password")

def show_main_app(auth_service):
    """Display main application interface."""
    user = auth_service.get_current_user()
    
    # Show page directly based on role - logout integrated in dashboard
    if user['role'] == 'admin':
        show_admin_interface(auth_service)
    else:
        show_intern_interface(auth_service)

def show_admin_interface(auth_service):
    """Display admin dashboard interface."""
    from views.admin_dashboard import show_admin_dashboard
    show_admin_dashboard(auth_service)

def show_intern_interface(auth_service):
    """Display intern dashboard interface."""
    # Direct dashboard without sidebar
    from views.intern_dashboard import show_intern_dashboard
    show_intern_dashboard(auth_service)

if __name__ == "__main__":
    main()