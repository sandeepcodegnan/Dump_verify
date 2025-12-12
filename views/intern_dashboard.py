"""Intern dashboard with multi-subject verification interface."""
import streamlit as st
from services.db_service import DatabaseService
from services.auth_service import AuthService
from utils.constants import SUBJECTS

def show_intern_dashboard(auth_service=None):
    """Display intern dashboard with multi-subject support."""
    if not auth_service:
        auth_service = AuthService()
    db_service = DatabaseService()
    
    user = auth_service.get_current_user()
    if not user or user['role'] != 'intern':
        st.error("Access denied. Intern role required.")
        return
    
    # Check if in verification mode
    if st.session_state.get('verification_mode', False):
        show_verification_page(db_service, user, auth_service)
        return
    
    # Header with integrated logout
    col1, col2 = st.columns([5, 1])
    with col1:
        st.header(f"🎯 Welcome, {user['name']}")
    with col2:
        if st.button("🚪 Logout", key="intern_logout"):
            auth_service.logout_user()
            st.rerun()
    
    # Get intern's assignments
    assignments = db_service.get_intern_assignments(user['user_id'])
    
    if not assignments:
        st.info("No assignments found. Please contact your administrator.")
        return
    
    # Progress Overview
    show_progress_overview(db_service, user['user_id'], assignments)
    
    # Subject Tabs with metrics only
    subject_tabs = st.tabs([f"📚 {subject.title()}" for subject in assignments['subjects']])
    
    for i, subject in enumerate(assignments['subjects']):
        with subject_tabs[i]:
            show_subject_metrics(db_service, user['user_id'], subject)

def show_progress_overview(db_service, intern_id, assignments):
    """Display progress overview for the intern."""
    st.subheader("📊 Your Progress")
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    
    total_assigned = sum(assignments['quotas'].values())
    stats = db_service.get_intern_stats(intern_id)
    total_completed = stats['verified'] + stats['modified']
    remaining = total_assigned - total_completed
    
    with col1:
        st.metric("Total Assigned", f"{total_assigned:,}")
    
    with col2:
        st.metric("Completed", f"{total_completed:,}", f"+{stats['verified']}")
    
    with col3:
        st.metric("Remaining", f"{remaining:,}")
    
    with col4:
        completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        st.metric("Progress", f"{completion_rate:.1f}%")
    
    # Progress by subject
    st.markdown("**Progress by Subject**")
    for subject in assignments['subjects']:
        subject_stats = db_service.get_intern_subject_stats(intern_id, subject)
        quota = assignments['quotas'].get(subject, 0)
        completed = subject_stats['verified'] + subject_stats['modified']
        progress = (completed / quota * 100) if quota > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress / 100, text=f"{subject.title()}: {completed}/{quota}")
        with col2:
            st.write(f"{progress:.1f}%")

def show_subject_metrics(db_service, intern_id, subject):
    """Display metrics and actions for a specific subject."""
    st.markdown(f"### 📝 {subject.title()} Overview")
    
    # Show metrics
    total_questions = db_service.get_subject_question_count(subject)
    verified_count = db_service.get_intern_subject_stats(intern_id, subject)
    completed = verified_count['verified'] + verified_count['modified']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", total_questions)
    with col2:
        st.metric("Completed", completed)
    with col3:
        st.metric("Remaining", total_questions - completed)
    
    # Progress bar
    if total_questions > 0:
        progress = completed / total_questions
        st.progress(progress, text=f"Progress: {progress*100:.1f}%")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"✏️ Start Verification", key=f"start_{subject}", type="primary", use_container_width=True):
            # Find first unverified question
            first_unverified = db_service.get_first_unverified_question_index(subject)
            st.session_state['verification_mode'] = True
            st.session_state['current_subject'] = subject
            st.session_state[f"{subject}_page"] = first_unverified
            if 'view_mode' in st.session_state:
                del st.session_state['view_mode']
            st.rerun()
    
    with col2:
        if st.button(f"📋 View All Questions", key=f"view_{subject}", use_container_width=True):
            st.session_state['verification_mode'] = True
            st.session_state['view_mode'] = True
            st.session_state['current_subject'] = subject
            st.rerun()

def show_verification_page(db_service, user, auth_service):
    """Display verification page."""
    subject = st.session_state.get('current_subject')
    
    if not subject:
        st.session_state['verification_mode'] = False
        st.rerun()
        return
    
    # Header with all buttons in single row
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"### ✏️ Verify {subject.title()} Questions")
    with col2:
        if st.button("🏠 Back to Dashboard"):
            st.session_state['verification_mode'] = False
            if 'current_subject' in st.session_state:
                del st.session_state['current_subject']
            if 'view_mode' in st.session_state:
                del st.session_state['view_mode']
            st.rerun()
    with col3:
        if st.button("📋 View All Mode", disabled=st.session_state.get('view_mode', False)):
            st.session_state['view_mode'] = True
            st.rerun()
    with col4:
        if st.button("🚪 Logout", key="verify_logout"):
            auth_service.logout_user()
            st.rerun()
    
    st.divider()
    
    # Show appropriate interface
    if st.session_state.get('view_mode', False):
        show_all_questions_list(db_service, subject)
    else:
        show_verification_interface(db_service, user['user_id'], subject)

def show_verification_interface(db_service, intern_id, subject):
    """Display the edit and verification interface for questions."""
    from components.question_editor import QuestionEditor
    
    # Initialize pagination
    session_key = f"{subject}_page"
    if session_key not in st.session_state:
        st.session_state[session_key] = 1
    
    # Get questions
    result = db_service.get_paginated_questions(
        subject, 
        page=st.session_state[session_key],
        size=1
    )
    
    if not result['questions']:
        st.success("🎉 All questions completed for this subject!")
        if st.button("🔙 Back to Subject"):
            st.session_state[f'verify_mode_{subject}'] = False
            st.rerun()
        return
    
    question = result['questions'][0]
    editor = QuestionEditor()
    
    # Question header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📝 Question {st.session_state[session_key]} of {result['total']}")
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Check if in edit mode
    edit_mode_key = f"edit_mode_{question['_id']}"
    
    # Display original question only if NOT in edit mode
    if not st.session_state.get(edit_mode_key, False):
        with st.expander("📖 Original Question", expanded=True):
            st.write(f"**Question:** {question.get('Question', 'No question text')}")
            
            if question.get('Options'):
                st.write("**Options:**")
                for key, value in question['Options'].items():
                    st.write(f"**{key}.** {value}")
                st.write(f"**Correct Answer:** {question.get('Correct_Option', 'Not specified')}")
            
            if question.get('Explanation'):
                st.write(f"**Explanation:** {question.get('Explanation')}")
    
    if st.session_state.get(edit_mode_key, False):
        # Compact edit layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📖 Original**")
            st.text(f"Q: {question.get('Question', 'No question text')[:100]}...")
            if question.get('Options'):
                for key, value in question['Options'].items():
                    st.text(f"{key}. {value[:50]}...")
                st.text(f"Answer: {question.get('Correct_Option', 'Not specified')}")
        
        with col2:
            st.markdown("**✏️ Editor**")
            question_text = st.text_area(
                "Question",
                value=question.get("Question", ""),
                key=f"edit_{question['_id']}_question",
                height=60
            )
            
            options = {}
            col_a, col_b = st.columns(2)
            with col_a:
                options['A'] = st.text_input("A", value=question.get("Options", {}).get('A', ""), key=f"edit_{question['_id']}_option_A")
                options['C'] = st.text_input("C", value=question.get("Options", {}).get('C', ""), key=f"edit_{question['_id']}_option_C")
            with col_b:
                options['B'] = st.text_input("B", value=question.get("Options", {}).get('B', ""), key=f"edit_{question['_id']}_option_B")
                options['D'] = st.text_input("D", value=question.get("Options", {}).get('D', ""), key=f"edit_{question['_id']}_option_D")
            
            col_ans, col_exp = st.columns(2)
            with col_ans:
                correct_option = st.selectbox(
                    "Answer",
                    options=['A', 'B', 'C', 'D'],
                    index=['A', 'B', 'C', 'D'].index(question.get("Correct_Option", "A")),
                    key=f"edit_{question['_id']}_correct"
                )
            with col_exp:
                explanation = st.text_input(
                    "Explanation",
                    value=question.get("Explanation", ""),
                    key=f"edit_{question['_id']}_explanation"
                )
            
            edited_data = {
                "Question": question_text,
                "Options": options,
                "Correct_Option": correct_option,
                "Explanation": explanation
            }
        
        # Compact action buttons
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("✅ Verify with Changes", type="primary", key=f"verify_changes_{question['_id']}", use_container_width=True):
                # Detect changes
                changes = {}
                for key, value in edited_data.items():
                    if str(question.get(key, "")) != str(value):
                        changes[key] = value
                
                if changes:
                    with st.spinner("Saving changes and verifying..."):
                        success = db_service.verify_question(
                            str(question['_id']), 
                            intern_id, 
                            "modified",
                            changes
                        )
                        if success:
                            st.success("✅ Question modified and verified!")
                            # Auto-advance to next question
                            st.session_state[session_key] = min(st.session_state[session_key] + 1, result['total'])
                            # Clear edit mode
                            if edit_mode_key in st.session_state:
                                del st.session_state[edit_mode_key]
                            st.rerun()
                        else:
                            st.error("❌ Verification failed")
                else:
                    st.warning("⚠️ No changes detected.")
        
        with btn_col2:
            if st.button("❌ Cancel Edit", key=f"cancel_edit_{question['_id']}", use_container_width=True):
                st.session_state[edit_mode_key] = False
                st.rerun()
    
    else:
        # Compact verification actions
        col1, col2, col3 = st.columns(3)
        
        # Check if question is already verified by checking verified collection
        already_processed = db_service.is_question_verified(str(question['_id']), subject)
        
        if already_processed:
            st.info("✅ This question is already verified")
        
        with col1:
            if st.button("✅ Verify", type="primary", key=f"verify_{question['_id']}", disabled=already_processed):
                with st.spinner("Verifying question..."):
                    success = db_service.verify_question(
                        str(question['_id']), 
                        intern_id, 
                        "verified"
                    )
                    if success:
                        st.success("✅ Question verified!")
                        # Auto-advance to next question
                        st.session_state[session_key] = min(st.session_state[session_key] + 1, result['total'])
                        st.rerun()
                    else:
                        st.error("❌ Verification failed")
        
        with col2:
            if st.button("📝 Modify & Verify", key=f"modify_{question['_id']}", disabled=already_processed):
                st.session_state[edit_mode_key] = True
                st.rerun()
        
        with col3:
            if st.button(f"🔙 Back", key=f"back_{subject}"):
                st.session_state['verification_mode'] = False
                if 'current_subject' in st.session_state:
                    del st.session_state['current_subject']
                if 'view_mode' in st.session_state:
                    del st.session_state['view_mode']
                st.rerun()
    
    # Compact navigation - only Previous button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("⬅️ Prev", disabled=st.session_state[session_key] <= 1):
            st.session_state[session_key] = max(1, st.session_state[session_key] - 1)
            st.rerun()
    with col2:
        st.write(f"Question {st.session_state[session_key]} of {result['total']}")

def show_subject_progress(db_service, intern_id, subject):
    """Show detailed progress for a subject."""
    st.markdown(f"#### 📊 {subject.title()} Progress")
    
    stats = db_service.get_intern_subject_stats(intern_id, subject)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Verified", stats['verified'])
    with col2:
        st.metric("Modified", stats['modified'])
    with col3:
        st.metric("Total", stats['verified'] + stats['modified'])



def show_all_questions_list(db_service, subject):
    """Show all questions in the subject for the intern."""
    st.markdown(f"#### 📋 All {subject.title()} Questions")
    
    # Get all questions with pagination
    page_size = 10
    page_key = f'list_page_{subject}'
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    
    result = db_service.get_paginated_questions(
        subject, 
        page=st.session_state[page_key],
        size=page_size
    )
    
    if result['questions']:
        st.info(f"Showing {len(result['questions'])} of {result['total']} unverified questions")
        
        for i, question in enumerate(result['questions'], 1):
            question_num = ((st.session_state[page_key] - 1) * page_size) + i
            with st.expander(f"Question {question_num}", expanded=False):
                st.write(f"**Question:** {question.get('Question', 'No text')}")
                
                if question.get('Options'):
                    for key, value in question['Options'].items():
                        st.write(f"**{key}.** {value}")
                    st.write(f"**Answer:** {question.get('Correct_Option')}")
                
                if question.get('Explanation'):
                    st.write(f"**Explanation:** {question.get('Explanation')}")
                
                st.caption(f"ID: {str(question['_id'])[:8]}...")
        
        # Pagination - only Previous button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("⬅️ Previous", key=f"prev_{subject}", disabled=st.session_state[page_key] <= 1):
                st.session_state[page_key] -= 1
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state[page_key]} of {result['total_pages']}")
    
    else:
        st.success("🎉 All questions completed for this subject!")

if __name__ == "__main__":
    show_intern_dashboard()