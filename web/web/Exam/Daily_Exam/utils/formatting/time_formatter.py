"""Time formatting utilities"""

class TimeFormatter:
    """Utility class for time formatting"""
    
    @staticmethod
    def format_seconds_to_minutes(seconds: int) -> str:
        """Format seconds to 'Xm Ys' format"""
        if seconds <= 0:
            return "0m 0s"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"