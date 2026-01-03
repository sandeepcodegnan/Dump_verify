"""Admin dashboard with real-time analytics and intern management."""
import streamlit as st
from services.db_service import DatabaseService
from services.auth_service import AuthService
from utils.constants import SUBJECTS
from datetime import datetime, timedelta

def show_admin_dashboard(auth_service=None):
    """Display comprehensive admin dashboard."""
    if not auth_service:
        auth_service = AuthService()
    db_service = DatabaseService()
    
    user = auth_service.get_current_user()
    if not user or user['role'] != 'admin':
        st.error("Access denied. Admin role required.")
        return
    
    # Header with integrated logout
    col1, col2 = st.columns([5, 1])
    with col1:
        st.header("📊 Admin Dashboard")
    with col2:
        if st.button("🚪 Logout", key="admin_logout"):
            auth_service.logout_user()
            st.rerun()
    
    # Quick Stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_questions = get_total_questions(db_service)
        st.metric("Total Questions", f"{total_questions:,}", "↗️ Active")
    
    with col2:
        verified_today = get_verified_today(db_service)
        st.metric("Verified Today", verified_today, "+12")
    
    with col3:
        active_interns = get_active_interns(db_service)
        st.metric("Active Interns", active_interns, "+2")
    
    with col4:
        completion_rate = get_completion_rate(db_service)
        st.metric("Completion Rate", f"{completion_rate}%", "+3%")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Analytics", "👥 Intern Management", "📊 Intern Progress", "📋 Collections", "⚙️ Settings"])
    
    with tab1:
        show_analytics_section(db_service)
    
    with tab2:
        show_intern_management(db_service)
    
    with tab3:
        show_intern_progress_section(db_service)
    
    with tab4:
        show_collections_overview(db_service)
    
    with tab5:
        show_system_settings()
    


def show_analytics_section(db_service):
    """Display analytics and performance metrics."""
    st.subheader("📈 Performance Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Verification Progress by Subject**")
        
        # Get actual subjects from database
        available_subjects = db_service.get_available_subjects()
        
        if available_subjects:
            for subject, total in available_subjects.items():
                verified = db_service.get_verified_count(subject)
                progress = (verified / total * 100) if total > 0 else 0
                st.progress(progress / 100, text=f"{subject.title()}: {progress:.1f}%")
        else:
            st.info("No subjects found in database")
    
    with col2:
        st.markdown("**Top Performing Interns**")
        top_interns = db_service.get_top_interns(limit=5)
        
        if top_interns:
            for i, intern in enumerate(top_interns, 1):
                st.write(f"{i}. **{intern['name']}** - {intern['verified']} verified")
        else:
            st.info("No verification activity yet")

def show_intern_management(db_service):
    """Display intern allocation and management interface."""
    st.subheader("👥 Intern Management")
    
    # Tabs for different operations
    tab1, tab2 = st.tabs(["🆕 Create Intern", "📎 Allocate Subjects"])
    
    with tab1:
        show_create_intern_interface(db_service)
    
    with tab2:
        show_allocation_interface(db_service)

def show_create_intern_interface(db_service):
    """Interface to create new intern users."""
    st.markdown("**Create New Intern**")
    
    # Get unallocated subjects only
    unallocated_subjects = db_service.get_unallocated_subjects()
    
    if not unallocated_subjects:
        st.warning("⚠️ No unallocated subjects available.")
        st.info("All available subjects are already allocated to interns. Use 'Allocate Subjects' tab to manage existing allocations.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        intern_name = st.text_input("Intern Name")
        intern_email = st.text_input("Email Address")
    
    with col2:
        selected_subjects = st.multiselect(
            "Allocate Subjects (Unallocated Only)",
            options=list(unallocated_subjects.keys()),
            format_func=lambda x: f"{x.title()} ({unallocated_subjects[x]} questions)"
        )
    
    if st.button("✅ Create Intern", type="primary"):
        if intern_name and intern_email and selected_subjects:
            # Create intern user
            user_data, error = db_service.create_intern_user(intern_name, intern_email, selected_subjects)
            
            if user_data:
                # Send email with credentials
                from services.email_service import EmailService
                email_service = EmailService()
                
                email_sent = email_service.send_intern_credentials(
                    intern_email,
                    intern_name,
                    user_data["username"],
                    user_data["password"],
                    selected_subjects
                )
                
                if email_sent:
                    st.success(f"✅ Intern created successfully! Credentials sent to {intern_email}")
                else:
                    st.success(f"✅ Intern created successfully! Username: {user_data['username']} | Password: {user_data['password']}")
                
                st.rerun()
            else:
                st.error(f"❌ {error}")
        else:
            st.warning("Please fill all fields and select at least one subject")

def show_allocation_interface(db_service):
    """Interface to allocate subjects to existing interns."""
    st.markdown("**Allocate Subjects to Existing Intern**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get available interns
        interns = db_service.get_all_interns()
        if not interns:
            st.warning("No interns found in the system.")
            return
            
        intern_options = {f"{intern['name']} ({intern['user_id']})": intern['user_id'] for intern in interns}
        selected_intern = st.selectbox("Select Intern", options=list(intern_options.keys()))
        
        # Get subjects not already allocated to this intern
        intern_id = intern_options[selected_intern]
        allocated_subjects = db_service.get_intern_allocated_subjects(intern_id)
        available_subjects = db_service.get_available_subjects()
        
        # Filter out already allocated subjects
        unallocated_subjects = {k: v for k, v in available_subjects.items() if k not in allocated_subjects}
        
        if not unallocated_subjects:
            st.info(f"All available subjects are already allocated to {selected_intern}")
            return
        
        st.markdown("**Select Subjects to Allocate:**")
        selected_subjects = st.multiselect(
            "Choose subjects",
            options=list(unallocated_subjects.keys()),
            format_func=lambda x: x.title()
        )
        
        if selected_subjects:
            # Show total questions that will be allocated
            total_questions = sum(unallocated_subjects[subject] for subject in selected_subjects)
        
        if selected_subjects:
            # Show total questions that will be allocated
            total_questions = sum(available_subjects[subject] for subject in selected_subjects)
            st.info(f"Total questions to allocate: {total_questions}")
            
            if st.button("✅ Allocate", type="primary"):
                # Create quotas with full counts for each subject
                quotas = {subject: unallocated_subjects[subject] for subject in selected_subjects}
                
                success = db_service.allocate_questions(intern_id, selected_subjects, quotas)
                if success:
                    st.success(f"✅ Allocated {len(selected_subjects)} complete subjects ({total_questions} questions) to {selected_intern}")
    
                    st.rerun()
                else:
                    st.error("Allocation failed")
    
    with col2:
        st.markdown("**Interns Overview**")
        
        # Get all interns
        all_interns = db_service.get_all_interns()
        
        if all_interns:
            st.info(f"Total Interns: {len(all_interns)}")
            
            for intern in all_interns:
                allocated_subjects = intern.get('allocated_subjects', [])
                
                if allocated_subjects:
                    subjects_text = ', '.join([s.title() for s in allocated_subjects])
                    st.write(f"🧑‍💻 **{intern['name']}**: {subjects_text}")
                else:
                    st.write(f"🧑‍💻 **{intern['name']}**: No subjects allocated")
        else:
            st.write("No interns found")

def show_intern_progress_section(db_service):
    """Display detailed progress for each intern."""
    st.subheader("📊 Individual Intern Progress")
    
    # Get all interns
    interns = db_service.get_all_interns()
    
    if not interns:
        st.info("No interns found in the system.")
        return
    
    # Summary stats and intern selection
    col1, col2, col3 = st.columns(3)
    active_interns = len([i for i in interns if i.get('allocated_subjects')])
    
    with col1:
        st.metric("Total Interns", len(interns))
    with col2:
        st.metric("Active Interns", active_interns)
    with col3:
        # Intern selection dropdown
        intern_options = [f"{intern['name']} ({intern['user_id']})" for intern in interns if intern.get('allocated_subjects')]
        if not intern_options:
            st.info("No active interns found.")
            return
            
        selected_intern_option = st.selectbox(
            "Select Intern",
            options=intern_options,
            index=0,
            key="intern_progress_selector"
        )
    
    st.divider()
    
    # Get selected intern
    selected_name = selected_intern_option.split(' (')[0]
    selected_intern = next(i for i in interns if i['name'] == selected_name)
    
    # Show detailed progress for selected intern only
    if selected_intern:
        show_detailed_intern_progress(db_service, selected_intern)

def show_detailed_intern_progress(db_service, intern):
    """Show detailed progress for a specific intern."""
    allocated_subjects = intern.get('allocated_subjects', [])
    if not allocated_subjects:
        st.warning("No subjects allocated to this intern")
        return
    
    # Calculate overall progress
    total_verified = 0
    total_assigned = 0
    for subject in allocated_subjects:
        subject_stats = db_service.get_intern_subject_stats(intern['user_id'], subject)
        total_questions = db_service.get_subject_question_count(subject)
        completed = subject_stats['verified'] + subject_stats['modified']
        total_verified += completed
        total_assigned += total_questions
    
    overall_progress = (total_verified / total_assigned * 100) if total_assigned > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Intern header
        st.markdown(f"### 👨💻 {intern['name']} ({intern['user_id']})")
    with col4:
        # Subject selection dropdown
        subject_options = []
        for subject in allocated_subjects:
            total_questions = db_service.get_subject_question_count(subject)
            subject_options.append((subject, f"{subject.title()}"))
        
        selected_subject = st.selectbox(
            "Select Subject",
            options=[opt[0] for opt in subject_options],
            format_func=lambda x: next(opt[1] for opt in subject_options if opt[0] == x),
            key=f"subject_selector_{intern['user_id']}",
            label_visibility="collapsed"
        )
    
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if overall_progress >= 90:
            st.success(f"✅ {overall_progress:.1f}%")
        elif overall_progress >= 70:
            st.info(f"🟡 {overall_progress:.1f}%")
        elif overall_progress >= 50:
            st.warning(f"🟠 {overall_progress:.1f}%")
        else:
            st.error(f"🔴 {overall_progress:.1f}%")
    with col2:
        st.metric("Total Completed", total_verified)
    with col3:
        st.metric("Total Assigned", total_assigned)
    with col4:
        st.metric("Remaining", total_assigned - total_verified)
    
    # Progress bar
    st.progress(min(1.0, overall_progress / 100), text=f"Overall Progress: {overall_progress:.1f}%")
    
    st.divider()
    
    # Subject-wise details
    col_title, col_dropdown = st.columns([1, 2])
    
    with col_title:
        st.markdown("**📚 Subject-wise Progress**")
    
    
    
    if selected_subject:
        subject_stats = db_service.get_intern_subject_stats(intern['user_id'], selected_subject)
        total_questions = db_service.get_subject_question_count(selected_subject)
        completed = subject_stats['verified'] + subject_stats['modified']
        subject_progress = (completed / total_questions * 100) if total_questions > 0 else 0
        
        # Performance indicators
        daily_avg = db_service.get_daily_average(intern['user_id'], selected_subject)
        questions_today = db_service.get_questions_today(intern['user_id'], selected_subject)
        last_activity = db_service.get_last_activity(intern['user_id'], selected_subject)
        
        # Subject progress bar
        st.progress(subject_progress / 100, text=f"Progress: {subject_progress:.1f}%")
        
        # First row - Progress and counts
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Total Questions", total_questions)
        with col_b:
            st.metric("Verified", subject_stats['verified'])
        with col_c:
            st.metric("Modified", subject_stats['modified'])
        with col_d:
            st.metric("Remaining", total_questions - completed)
        
        # Second row - Performance and activity
        col_e, col_f, col_g, col_h = st.columns(4)
        with col_e:
            st.metric("Daily Avg", f"{daily_avg:.1f}")
        with col_f:
            st.metric("Today", questions_today)
        with col_g:
            st.metric("Re-verified", subject_stats['reverified'])
        with col_h:
            st.metric("Last Activity", last_activity or "Never")

            
def show_collections_overview(db_service):
    """Display enhanced collections status and management."""
    st.subheader("📋 Collections Overview")
    
    # Get actual collections from database
    available_subjects = db_service.get_available_subjects()
    
    if not available_subjects:
        st.info("No collections found")
        return
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    total_questions = sum(available_subjects.values())
    total_verified = sum(db_service.get_verified_count(subject) for subject in available_subjects.keys())
    completion_rate = (total_verified / total_questions * 100) if total_questions > 0 else 0
    
    with col1:
        st.metric("Total Collections", len(available_subjects))
    with col2:
        st.metric("Total Questions", f"{total_questions:,}")
    with col3:
        st.metric("Verified Questions", f"{total_verified:,}")
    with col4:
        st.metric("Overall Progress", f"{completion_rate:.1f}%")
    
    st.divider()
    
    # Collections table with enhanced info
    st.markdown("**📊 Collection Details**")
    
    for subject, total_count in available_subjects.items():
        verified_count = db_service.get_verified_count(subject)
        progress = (verified_count / total_count * 100) if total_count > 0 else 0
        remaining = total_count - verified_count
        
        with st.expander(f"📚 {subject.title()} Collection", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Progress bar
                st.progress(progress / 100, text=f"Progress: {progress:.1f}%")
                
                # Stats row
                stat_col1, stat_col2, stat_col3 = st.columns(3)
                with stat_col1:
                    st.metric("Total", f"{total_count:,}")
                with stat_col2:
                    st.metric("Verified", f"{verified_count:,}")
                with stat_col3:
                    st.metric("Remaining", f"{remaining:,}")
            
            with col2:
                # Status indicator
                if progress >= 100:
                    st.success("✅ Complete")
                elif progress >= 75:
                    st.info("🟡 Near Complete")
                elif progress >= 25:
                    st.warning("🟠 In Progress")
                else:
                    st.error("🔴 Just Started")

def show_system_settings():
    """Display system configuration settings."""
    st.subheader("⚙️ System Settings")
    
    st.markdown("**Day Locking Configuration**")
    
    import os
    current_setting = os.getenv('ENABLE_DAY_LOCKING', 'true').lower() == 'true'
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        day_locking_enabled = st.checkbox(
            "Enable Sequential Day Locking",
            value=current_setting,
            help="When enabled, interns must complete current day before accessing next day. When disabled, all days are available."
        )
        
        if day_locking_enabled != current_setting:
            if st.button("⚙️ Update Setting", type="primary"):
                # Update environment variable
                new_value = 'true' if day_locking_enabled else 'false'
                update_env_setting('ENABLE_DAY_LOCKING', new_value)
                st.success(f"✅ Day locking {'enabled' if day_locking_enabled else 'disabled'} successfully!")
                st.info("🔄 Setting will take effect for new sessions.")
                st.rerun()
    
    with col2:
        st.info(
            "📝 **Day Locking Modes:**\n\n"
            "✅ **Enabled**: Sequential unlocking\n"
            "❌ **Disabled**: All days available"
        )

def update_env_setting(key, value):
    """Update environment variable in .env file."""
    import os
    
    # Find .env file automatically
    env_path = None
    current_dir = os.getcwd()
    
    # Check current directory and parent directories
    for _ in range(3):  # Check up to 3 levels up
        test_path = os.path.join(current_dir, '.env')
        if os.path.exists(test_path):
            env_path = test_path
            break
        current_dir = os.path.dirname(current_dir)
    
    if not env_path:
        env_path = '.env'  # Fallback to current directory
    
    # Read current .env file
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Update or add the setting
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            updated = True
            break
    
    if not updated:
        lines.append(f'{key}={value}\n')
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    # Update current environment
    os.environ[key] = value

def show_audit_logs(db_service):
    """Display audit logs and activity tracking."""
    st.subheader("🔍 Audit Logs")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_filter = st.date_input("From Date", value=datetime.now() - timedelta(days=7))
    
    with col2:
        action_filter = st.selectbox("Action", ["All", "verified", "modified"])
    
    with col3:
        intern_filter = st.selectbox("Intern", ["All"] + [intern['name'] for intern in db_service.get_all_interns()])
    
    # Get audit logs
    logs = db_service.get_audit_logs(
        date_from=date_filter,
        action=action_filter if action_filter != "All" else None,
        intern=intern_filter if intern_filter != "All" else None,
        limit=50
    )
    
    # Display logs
    for log in logs:
        with st.expander(f"{log['question_id']} - {log['action']} by {log['intern_id']}"):
            st.write(f"**Time**: {log['timestamp']}")
            st.write(f"**Action**: {log['action']}")
            if log.get('changes'):
                st.write("**Changes**:")
                st.json(log['changes'])

# Helper functions
def get_total_questions(db_service):
    """Get total questions across all subjects."""
    available_subjects = db_service.get_available_subjects()
    return sum(available_subjects.values()) if available_subjects else 0

def get_verified_today(db_service):
    """Get questions verified today."""
    return db_service.get_verified_today_count()

def get_active_interns(db_service):
    """Get count of active interns."""
    return len(db_service.get_all_interns())

def get_completion_rate(db_service):
    """Calculate overall completion rate."""
    return round(db_service.get_overall_completion_rate(), 1)

if __name__ == "__main__":
    show_admin_dashboard()