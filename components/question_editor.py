"""Question editor component for verification interface."""
import streamlit as st

def render_question_image(question_data):
    """Render question image if Image_URL exists."""
    image_url = question_data.get("Image_URL")
    if image_url:
        try:
            st.image(image_url, caption="📷 Question Image", width=400)
        except:
            st.error("❌ Image not accessible")
    return image_url

class QuestionEditor:
    def __init__(self):
        pass
    
    def render_mcq_editor(self, question_data, key_prefix=""):
        """Render MCQ question editor with image support."""
        with st.container():
            st.markdown("### 📝 MCQ Question Editor")
            
            # Question text
            question_text = st.text_area(
                "Question",
                value=question_data.get("Question", ""),
                key=f"{key_prefix}_question",
                height=100
            )
            
            # Image upload for aptitude questions
            current_image_url = question_data.get("Image_URL", "")
            
            # Show current image if exists
            if current_image_url:
                try:
                    st.image(current_image_url, caption="Current Image", width=400)
                except:
                    st.error("❌ Current image not accessible")
            
            # File uploader
            uploaded_file = st.file_uploader(
                "Upload New Image (optional)",
                type=['png', 'jpg', 'jpeg'],
                key=f"{key_prefix}_image_upload",
                help="Upload image for questions that require visual elements"
            )
            
            # Handle image upload
            new_image_url = current_image_url
            if uploaded_file:
                from services.s3_service import S3Service
                s3_service = S3Service()
                
                with st.spinner("Uploading image..."):
                    # Reset file pointer
                    uploaded_file.seek(0)
                    new_image_url = s3_service.upload_image(uploaded_file)
                    
                    if new_image_url:
                        st.success("✅ Image uploaded successfully!")
                        try:
                            st.image(new_image_url, caption="Uploaded Image", width=400)
                        except:
                            st.warning("⚠️ Image uploaded but preview failed")
                    else:
                        st.error("❌ Image upload failed")
                        new_image_url = current_image_url
            
            # Options in A, B, C, D order
            st.markdown("**Options:**")
            options = {}
            for option_key in ['A', 'B', 'C', 'D']:
                options[option_key] = st.text_input(
                    f"Option {option_key}",
                    value=question_data.get("Options", {}).get(option_key, ""),
                    key=f"{key_prefix}_option_{option_key}"
                )
            
            # Correct answer
            correct_option = st.selectbox(
                "Correct Answer",
                options=['A', 'B', 'C', 'D'],
                index=['A', 'B', 'C', 'D'].index(question_data.get("Correct_Option", "A")),
                key=f"{key_prefix}_correct"
            )
            
            # Explanation
            explanation = st.text_area(
                "Explanation",
                value=question_data.get("Explanation", ""),
                key=f"{key_prefix}_explanation",
                height=80
            )
            
            result = {
                "Question": question_text,
                "Options": options,
                "Correct_Option": correct_option,
                "Explanation": explanation
            }
            
            # Include Image_URL only if provided
            if new_image_url and new_image_url.strip():
                result["Image_URL"] = new_image_url.strip()
            elif current_image_url and not uploaded_file:
                # Keep existing image if no new upload
                result["Image_URL"] = current_image_url
            
            return result
    
    def render_code_editor(self, question_data, key_prefix=""):
        """Render code question editor."""
        with st.container():
            st.markdown("### 💻 Code Question Editor")
            
            # Question text
            question_text = st.text_area(
                "Question",
                value=question_data.get("Question", ""),
                key=f"{key_prefix}_question",
                height=100
            )
            
            # Code snippet
            code_snippet = st.text_area(
                "Code Snippet",
                value=question_data.get("Code", ""),
                key=f"{key_prefix}_code",
                height=200
            )
            
            # Expected output
            expected_output = st.text_area(
                "Expected Output",
                value=question_data.get("Expected_Output", ""),
                key=f"{key_prefix}_output",
                height=100
            )
            
            return {
                "Question": question_text,
                "Code": code_snippet,
                "Expected_Output": expected_output
            }
    
    def render_verification_actions(self, key_prefix=""):
        """Render verification action buttons."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            verify_direct = st.button(
                "✅ Verify as-is",
                key=f"{key_prefix}_verify",
                use_container_width=True
            )
        
        with col2:
            verify_modified = st.button(
                "📝 Verify with changes",
                key=f"{key_prefix}_modify",
                use_container_width=True
            )
        
        with col3:
            skip = st.button(
                "⏭️ Skip",
                key=f"{key_prefix}_skip",
                use_container_width=True
            )
        
        return {
            "verify_direct": verify_direct,
            "verify_modified": verify_modified,
            "skip": skip
        }