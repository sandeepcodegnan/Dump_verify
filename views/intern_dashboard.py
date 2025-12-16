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
            st.session_state['verification_mode'] = True
            st.session_state['current_subject'] = subject
            st.session_state['reverify_mode'] = False
            # Reset day selection to show day picker
            if 'selected_day' in st.session_state:
                del st.session_state['selected_day']
            if 'view_mode' in st.session_state:
                del st.session_state['view_mode']
            st.rerun()
    
    with col2:
        if st.button(f"🔄 Re-verify Questions", key=f"reverify_{subject}", use_container_width=True):
            st.session_state['verification_mode'] = True
            st.session_state['current_subject'] = subject
            st.session_state['reverify_mode'] = True
            # Reset day selection to show day picker
            if 'selected_day' in st.session_state:
                del st.session_state['selected_day']
            if 'view_mode' in st.session_state:
                del st.session_state['view_mode']
            st.rerun()

def show_verification_page(db_service, user, auth_service):
    """Display verification page with day-based organization."""
    subject = st.session_state.get('current_subject')
    
    if not subject:
        st.session_state['verification_mode'] = False
        st.rerun()
        return
    
    # Header with buttons
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        st.markdown(f"### ✏️ Verify {subject.title()} Questions")
    with col2:
        if st.button("🏠 Back to Dashboard"):
            st.session_state['verification_mode'] = False
            if 'current_subject' in st.session_state:
                del st.session_state['current_subject']
            st.rerun()
    with col3:
        if st.button("🚪 Logout", key="verify_logout"):
            auth_service.logout_user()
            st.rerun()
    
    st.divider()
    
    # Show day selection interface
    if not st.session_state.get('selected_day'):
        show_day_selection(db_service, subject)
    else:
        show_day_verification_interface(db_service, user['user_id'], subject)

def show_day_selection(db_service, subject):
    """Show available days for the subject."""
    reverify_mode = st.session_state.get('reverify_mode', False)
    
    if reverify_mode:
        st.markdown("### 🔄 Select Day to Re-verify")
        st.info("Re-verification mode: Work on already verified questions")
    else:
        st.markdown("### 📅 Select Day to Verify")
    
    # Get available days
    days = db_service.get_available_days(subject, include_verified=reverify_mode)
    
    if not days:
        if reverify_mode:
            st.info("No verified questions found for this subject.")
        else:
            st.info("No unverified questions found for this subject.")
        return
    
    # Filter days based on mode requirements
    if reverify_mode:
        # Only show days with verified questions
        valid_days = []
        for day in days:
            day_num = day.replace('day-', '')
            stats = db_service.get_day_stats(subject, day_num)
            if stats['verified'] > 0:
                valid_days.append((day, stats))
        
        if not valid_days:
            st.info("No days with verified questions found.")
            return
        
        # Display only valid days
        cols = st.columns(min(len(valid_days), 4))
        for i, (day, stats) in enumerate(valid_days):
            with cols[i % 4]:
                day_num = day.replace('day-', '')
                st.markdown(f"**{day.title()}**")
                st.write(f"📝 Total: {stats['total']}")
                st.write(f"✅ Verified: {stats['verified']}")
                st.write(f"⏳ Remaining: {stats['remaining']}")
                
                if st.button(f"Re-verify {day}", key=f"reverify_{day}", use_container_width=True):
                    st.session_state['selected_day'] = day_num
                    page_key = f"{subject}_day_{day_num}_page"
                    st.session_state[page_key] = 1
                    st.rerun()
    else:
        # Sequential day unlocking - only enable next day after current is completed
        all_day_stats = []
        for day in days:
            day_num = day.replace('day-', '')
            stats = db_service.get_day_stats(subject, day_num)
            all_day_stats.append((day, day_num, stats))
        
        # Sort by day number (convert to int for proper sorting)
        all_day_stats.sort(key=lambda x: int(x[1]) if x[1].isdigit() else 999)
        
        if not all_day_stats:
            st.info("No questions found for this subject.")
            return
        
        # Check if day locking is enabled
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
        
        # Load environment variables from found .env file
        if env_path:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        
        day_locking_enabled = os.getenv('ENABLE_DAY_LOCKING', 'true').lower() == 'true'
        
        # Find first incomplete day (only if locking enabled)
        if day_locking_enabled:
            current_day_index = len(all_day_stats)  # Default to end if all completed
            for i, (day, day_num, stats) in enumerate(all_day_stats):
                if stats['remaining'] > 0:
                    current_day_index = i
                    break
        else:
            current_day_index = -1  # Allow all days when locking disabled
        
        # Check if all days completed (only when locking enabled)
        if day_locking_enabled and current_day_index >= len(all_day_stats):
            st.success("🎉 All questions completed!")
            # Show final progress
            final_completed = len(all_day_stats)
            st.info(f"📊 Final Progress: {final_completed}/{len(all_day_stats)} days completed!")
            return
        
        # Display all days but only enable current day
        cols = st.columns(min(len(all_day_stats), 4))
        for i, (day, day_num, stats) in enumerate(all_day_stats):
            with cols[i % 4]:
                is_current = i == current_day_index
                is_completed = stats['remaining'] == 0
                is_locked = i > current_day_index
                
                # Day status styling
                if is_completed:
                    st.markdown(f"**✅ {day.title()}** (Completed)")
                elif not day_locking_enabled:
                    st.markdown(f"**📅 {day.title()}** (Available)")
                elif is_current:
                    st.markdown(f"**🔓 {day.title()}** (Current)")
                else:
                    st.markdown(f"**🔒 {day.title()}** (Locked)")
                
                st.write(f"📝 Total: {stats['total']}")
                st.write(f"✅ Verified: {stats['verified']}")
                st.write(f"⏳ Remaining: {stats['remaining']}")
                
                # Enable button based on locking policy
                if not day_locking_enabled:
                    # All days available when locking disabled
                    if st.button(f"Start {day}", key=f"start_{day}", use_container_width=True, type="primary" if not is_completed else "secondary"):
                        st.session_state['selected_day'] = day_num
                        page_key = f"{subject}_day_{day_num}_page"
                        st.session_state[page_key] = 1
                        st.rerun()
                elif is_current:
                    if st.button(f"Start {day}", key=f"start_{day}", use_container_width=True, type="primary"):
                        st.session_state['selected_day'] = day_num
                        page_key = f"{subject}_day_{day_num}_page"
                        st.session_state[page_key] = 1
                        st.rerun()
                elif is_completed:
                    st.success("Completed ✅")
                else:
                    st.button(f"Locked 🔒", key=f"locked_{day}", use_container_width=True, disabled=True)
        
        # Show progress info with debug
        completed_days = 0
        for i, (day, day_num, stats) in enumerate(all_day_stats):
            if stats['remaining'] == 0:
                completed_days += 1
        
        # Alternative calculation: all days before current day should be completed
        completed_days_alt = current_day_index
        
        current_day_num = all_day_stats[current_day_index][1] if current_day_index < len(all_day_stats) else "N/A"
        
        # Calculate completed days based on first day number
        first_day_num = int(all_day_stats[0][1]) if all_day_stats else 1
        actual_completed = max(0, first_day_num - 1)  # Days before first available day are completed
        
        if actual_completed > 0:
            st.success(f"🎉 {actual_completed} days completed!")
        
        if day_locking_enabled:
            st.info(f"📊 Progress: {actual_completed}/{len(all_day_stats)} days completed. Complete Day-{current_day_num} to unlock the next day.")
        else:
            st.info(f"📊 Progress: {actual_completed}/{len(all_day_stats)} days completed. All days are available.")

def show_day_verification_interface(db_service, intern_id, subject):
    """Display the edit and verification interface for day questions."""
    from components.question_editor import QuestionEditor
    
    selected_day = st.session_state.get('selected_day')
    if not selected_day:
        return
    
    # Day header with back button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 📅 Day-{selected_day} Questions")
    with col2:
        if st.button("🔙 Back to Days"):
            if 'selected_day' in st.session_state:
                del st.session_state['selected_day']
            st.rerun()
    
    # Get day questions based on mode
    reverify_mode = st.session_state.get('reverify_mode', False)
    questions = db_service.get_day_questions(subject, selected_day, include_verified=reverify_mode)
    
    # Filter questions based on mode
    if reverify_mode:
        questions = [q for q in questions if q.get('Q_id')]  # Only verified questions
        if not questions:
            st.success(f"🎉 No verified questions found for Day-{selected_day}!")
            return
    else:
        questions = [q for q in questions if not q.get('Q_id')]  # Only unverified questions
        if not questions:
            st.success(f"🎉 All Day-{selected_day} questions completed!")
            return
    
    # Initialize pagination for this day
    session_key = f"{subject}_day_{selected_day}_page"
    if session_key not in st.session_state:
        st.session_state[session_key] = 1
    
    # Get current question
    current_index = st.session_state[session_key] - 1
    if current_index >= len(questions):
        st.session_state[session_key] = 1
        current_index = 0
    
    question = questions[current_index]
    
    editor = QuestionEditor()
    
    # Question header with day info
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        tag = question.get('Tags', 'No tag')
        difficulty = question.get('Difficulty', 'Unknown')
        st.info(f"📝 Question {current_index + 1} of {len(questions)} | {tag} | 🎯 {difficulty}")
    with col2:
        # Show difficulty badge
        if difficulty == 'Easy':
            st.success(f"🟢 {difficulty}")
        elif difficulty == 'Medium':
            st.warning(f"🟡 {difficulty}")
        elif difficulty == 'Hard':
            st.error(f"🔴 {difficulty}")
        else:
            st.info(f"⚪ {difficulty}")
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Check if in edit mode
    edit_mode_key = f"edit_mode_{question['_id']}"
    
    # Display original question only if NOT in edit mode
    if not st.session_state.get(edit_mode_key, False):
        reverify_mode = st.session_state.get('reverify_mode', False)
        
        if reverify_mode:
            # Question selector dropdown for re-verification
            with st.expander("🔄 Select Question to Re-verify", expanded=True):
                question_options = []
                for i, q in enumerate(questions):
                    q_text = q.get('Question', 'No question text')[:80] + "..."
                    question_options.append(f"Q{i+1}: {q_text}")
                
                selected_index = st.selectbox(
                    "Choose question:",
                    range(len(questions)),
                    index=current_index,
                    format_func=lambda x: question_options[x],
                    key=f"question_selector_{selected_day}"
                )
                
                # Update session state if selection changed
                if selected_index != current_index:
                    st.session_state[session_key] = selected_index + 1
                    st.rerun()
                
                # Show selected question details
                st.write(f"**Question:** {question.get('Question', 'No question text')}")
                
                # Display image if exists
                if question.get('Image_URL'):
                    try:
                        st.image(question['Image_URL'], caption="📷 Question Image", width=400)
                    except:
                        st.error("❌ Image not accessible")
                
                if question.get('Options'):
                    st.write("**Options:**")
                    for key in ['A', 'B', 'C', 'D']:
                        if key in question['Options']:
                            st.write(f"**{key}.** {question['Options'][key]}")
                    st.write(f"**Correct Answer:** {question.get('Correct_Option', 'Not specified')}")
                
                explanation = question.get('Text_Explanation', '') or question.get('Explanation', '')
                if explanation:
                    st.write(f"**Explanation:** {explanation}")
        else:
            # Normal verification mode - show original question
            with st.expander("📖 Original Question", expanded=True):
                st.write(f"**Question:** {question.get('Question', 'No question text')}")
                
                # Display image if exists
                if question.get('Image_URL'):
                    try:
                        st.image(question['Image_URL'], caption="📷 Question Image", width=400)
                    except:
                        st.error("❌ Image not accessible")
                
                if question.get('Options'):
                    st.write("**Options:**")
                    for key in ['A', 'B', 'C', 'D']:
                        if key in question['Options']:
                            st.write(f"**{key}.** {question['Options'][key]}")
                    st.write(f"**Correct Answer:** {question.get('Correct_Option', 'Not specified')}")
                
                explanation = question.get('Text_Explanation', '') or question.get('Explanation', '')
                if explanation:
                    st.write(f"**Explanation:** {explanation}")
    
    if st.session_state.get(edit_mode_key, False):
        # Compact edit layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📖 Original**")
            st.text(f"Q: {question.get('Question', 'No question text')[:100]}...")
            
            # Show image thumbnail if exists
            if question.get('Image_URL'):
                try:
                    st.image(question['Image_URL'], width=120, caption="Original Image")
                except:
                    st.text("❌ Image not accessible")
            
            if question.get('Options'):
                for key in ['A', 'B', 'C', 'D']:
                    if key in question.get('Options', {}):
                        value = question['Options'][key]
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
            
            # Image upload editor - only for questions with existing Image_URL
            current_image_url = question.get("Image_URL", "")
            new_image_url = current_image_url
            
            if current_image_url:  # Only show image upload if question has Image_URL
                # Current image display
                try:
                    st.image(current_image_url, width=120, caption="Current Image")
                except:
                    st.error("❌ Image not accessible")
                
                # Image upload editor
                uploaded_file = st.file_uploader(
                    "Upload New Image",
                    type=['png', 'jpg', 'jpeg'],
                    key=f"edit_{question['_id']}_image_upload",
                    help="Upload new image to replace current one"
                )
                
                # Handle image upload
                if uploaded_file:
                    from services.s3_service import S3Service
                    s3_service = S3Service()
                    
                    with st.spinner("Uploading..."):
                        # Reset file pointer
                        uploaded_file.seek(0)
                        new_image_url = s3_service.upload_image(uploaded_file)
                        
                        if new_image_url:
                            st.success("✅ Uploaded!")
                            try:
                                st.image(new_image_url, width=120, caption="New Image")
                            except:
                                st.warning("⚠️ Uploaded but preview failed")
                        else:
                            st.error("❌ Upload failed")
                            new_image_url = current_image_url
            
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
                explanation = st.text_area(
                    "Explanation",
                    value=question.get("Text_Explanation", "") or question.get("Explanation", ""),
                    key=f"edit_{question['_id']}_explanation",
                    height=80
                )
            
            edited_data = {
                "Question": question_text,
                "Options": options,
                "Correct_Option": correct_option,
                "Explanation": explanation
            }
            
            # Include Image_URL in edited data only if question originally had image
            if current_image_url:  # Only include if question originally had Image_URL
                if new_image_url and new_image_url.strip():
                    edited_data["Image_URL"] = new_image_url.strip()
                else:
                    edited_data["Image_URL"] = current_image_url
        
        # Compact action buttons
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            reverify_mode = st.session_state.get('reverify_mode', False)
            if reverify_mode:
                if st.button("🔄 Re-verify with Changes", type="primary", key=f"reverify_changes_{question['_id']}", use_container_width=True):
                    # Detect changes including Image_url
                    changes = {}
                    for key, value in edited_data.items():
                        if str(question.get(key, "")) != str(value):
                            changes[key] = value
                    
                    # Handle Image_url removal
                    if not image_url.strip() and question.get("Image_url"):
                        changes["Image_url"] = ""
                    
                    if changes:
                        with st.spinner("Saving changes and re-verifying..."):
                            success, message = db_service.reverify_question(
                                str(question['_id']), 
                                intern_id, 
                                "remodified",
                                changes
                            )
                            if success:
                                st.success("🔄 Question re-modified!")
                                st.session_state[session_key] = min(st.session_state[session_key] + 1, len(questions))
                                if edit_mode_key in st.session_state:
                                    del st.session_state[edit_mode_key]
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ No changes detected.")
            else:
                if st.button("✅ Verify with Changes", type="primary", key=f"verify_changes_{question['_id']}", use_container_width=True):
                    # Detect changes including Image_url
                    changes = {}
                    for key, value in edited_data.items():
                        if str(question.get(key, "")) != str(value):
                            changes[key] = value
                    
                    # Handle Image_url removal
                    if not image_url.strip() and question.get("Image_url"):
                        changes["Image_url"] = ""
                    
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
                                st.session_state[session_key] = min(st.session_state[session_key] + 1, len(questions))
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
        
        reverify_mode = st.session_state.get('reverify_mode', False)
        already_processed = db_service.is_question_verified(str(question['_id']), subject)
        
        if already_processed and not reverify_mode:
            st.info("✅ This question is already verified")
        
        with col1:
            if reverify_mode:
                if st.button("🔄 Re-verify", type="primary", key=f"reverify_{question['_id']}"):
                    with st.spinner("Re-verifying question..."):
                        success, message = db_service.reverify_question(
                            str(question['_id']), 
                            intern_id, 
                            "reverified"
                        )
                        if success:
                            st.success("🔄 Question re-verified!")
                            st.session_state[session_key] = min(st.session_state[session_key] + 1, len(questions))
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            else:
                if st.button("✅ Verify", type="primary", key=f"verify_{question['_id']}", disabled=already_processed):
                    with st.spinner("Verifying question..."):
                        success = db_service.verify_question(
                            str(question['_id']), 
                            intern_id, 
                            "verified"
                        )
                        if success:
                            st.success("✅ Question verified!")
                            st.session_state[session_key] = min(st.session_state[session_key] + 1, len(questions))
                            st.rerun()
                        else:
                            st.error("❌ Verification failed")
        
        with col2:
            if reverify_mode:
                if st.button("📝 Re-modify", key=f"remodify_{question['_id']}"):
                    st.session_state[edit_mode_key] = True
                    st.rerun()
            else:
                if st.button("📝 Modify & Verify", key=f"modify_{question['_id']}", disabled=already_processed):
                    st.session_state[edit_mode_key] = True
                    st.rerun()
        
        with col3:
            if st.button(f"🔙 Back to Days", key=f"back_{subject}"):
                if 'selected_day' in st.session_state:
                    del st.session_state['selected_day']
                st.rerun()
    
    # Compact navigation (only show in normal verification mode)
    if not st.session_state.get('reverify_mode', False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Prev", disabled=st.session_state[session_key] <= 1):
                st.session_state[session_key] = max(1, st.session_state[session_key] - 1)
                st.rerun()
        with col2:
            st.write(f"Question {st.session_state[session_key]} of {len(questions)}")
        with col3:
            if st.button("➡️ Next", disabled=st.session_state[session_key] >= len(questions)):
                st.session_state[session_key] = min(st.session_state[session_key] + 1, len(questions))
                st.rerun()

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







if __name__ == "__main__":
    show_intern_dashboard()