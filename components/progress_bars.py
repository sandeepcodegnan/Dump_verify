"""Progress bar components for real-time tracking."""
import streamlit as st

class ProgressTracker:
    def __init__(self):
        pass
    
    def render_subject_progress(self, subject, completed, total, color="normal"):
        """Render progress bar for a subject."""
        progress = (completed / total) if total > 0 else 0
        
        # Color mapping
        color_map = {
            "normal": "#2563eb",
            "success": "#10b981", 
            "warning": "#f59e0b",
            "danger": "#ef4444"
        }
        
        # Custom CSS for colored progress bar
        if color != "normal":
            st.markdown(f"""
            <style>
            .stProgress > div > div > div > div {{
                background-color: {color_map.get(color, "#2563eb")};
            }}
            </style>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.progress(progress, text=f"{subject.title()}: {completed}/{total}")
        
        with col2:
            percentage = progress * 100
            st.write(f"{percentage:.1f}%")
        
        return progress
    
    def render_circular_progress(self, value, max_value, label="Progress"):
        """Render circular progress indicator."""
        percentage = (value / max_value * 100) if max_value > 0 else 0
        
        # Simple circular progress using HTML/CSS
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="
                width: 60px; 
                height: 60px; 
                border-radius: 50%; 
                background: conic-gradient(#2563eb {percentage}%, #e5e7eb {percentage}%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                color: #1e293b;
            ">
                <div style="
                    width: 45px; 
                    height: 45px; 
                    border-radius: 50%; 
                    background: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                ">
                    {percentage:.0f}%
                </div>
            </div>
            <div>
                <strong>{label}</strong><br>
                {value}/{max_value}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_streak_indicator(self, streak_count, max_streak=10):
        """Render streak indicator with icons."""
        filled_stars = min(streak_count, max_streak)
        empty_stars = max_streak - filled_stars
        
        stars = "⭐" * filled_stars + "☆" * empty_stars
        
        st.markdown(f"""
        <div style="text-align: center; padding: 10px;">
            <div style="font-size: 20px;">{stars}</div>
            <div style="font-size: 14px; color: #64748b;">
                Streak: {streak_count} days
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_achievement_badges(self, achievements):
        """Render achievement badges."""
        if not achievements:
            st.info("No achievements yet. Keep verifying to earn badges!")
            return
        
        badge_html = "<div style='display: flex; gap: 10px; flex-wrap: wrap;'>"
        
        for achievement in achievements:
            badge_html += f"""
            <div style='
                background: linear-gradient(45deg, #2563eb, #1d4ed8);
                color: white;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 5px;
            '>
                {achievement.get('icon', '🏆')} {achievement.get('name', 'Achievement')}
            </div>
            """
        
        badge_html += "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)