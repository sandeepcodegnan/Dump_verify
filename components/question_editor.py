"""Question editor component for verification interface."""
import streamlit as st

class QuestionEditor:
    def __init__(self):
        pass
    
    def render_mcq_editor(self, question_data, key_prefix=""):
        """Render MCQ question editor."""
        with st.container():
            st.markdown("### 📝 MCQ Question Editor")
            
            # Question text
            question_text = st.text_area(
                "Question",
                value=question_data.get("Question", ""),
                key=f"{key_prefix}_question",
                height=100
            )
            
            # Options
            st.markdown("**Options:**")
            options = {}
            for i, option_key in enumerate(['A', 'B', 'C', 'D']):
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
            
            return {
                "Question": question_text,
                "Options": options,
                "Correct_Option": correct_option,
                "Explanation": explanation
            }
    
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