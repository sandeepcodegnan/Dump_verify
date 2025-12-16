"""Leaderboard Formatter - Handles leaderboard data formatting"""
from typing import Dict, List
from web.Exam.Daily_Exam.services.common.image_service import ImageService
from web.Exam.Daily_Exam.utils.formatting.time_formatter import TimeFormatter

class LeaderboardFormatter:
    """Formats raw exam results into leaderboard data"""
    
    def __init__(self, image_service: ImageService):
        self.image_service = image_service
    
    def format_leaderboard(self, results: List[Dict]) -> List[Dict]:
        """Format raw results into leaderboard with rankings"""
        students_list = []
        
        for student in results:
            # Get image URL for student profile
            image_url = self.image_service.get_student_image_url(student.get("cgStudentId"))
            
            # Format time
            avg_time = student.get('avgTimeTaken', 0)
            time_formatted = TimeFormatter.format_seconds_to_minutes(avg_time)
            
            student_data = {
                "name": student["studentName"],
                "score": student["totalScore"],
                "avgTimeTaken": time_formatted,
                "examCount": student["examCount"],
                "attempted": student["attempted"],
                "studentId": student["studentId"],
                "cgStudentId": student.get("cgStudentId"),
                "imageUrl": image_url,
                "_time_seconds": int(avg_time)  # For sorting
            }
            
            students_list.append(student_data)
        
        # Filter only attempted students
        attempted = [s for s in students_list if s["attempted"]]
        
        # Sort attempted students by score, time, and name
        attempted.sort(key=lambda x: (
            -x["score"],        # Higher scores first
            x["_time_seconds"],  # Lower time first
            x["name"] or ""     # Alphabetical by name
        ))
        
        # Assign ranks
        leaderboard = []
        for rank, student in enumerate(attempted, 1):
            student["rank"] = rank
            student.pop("_time_seconds", None)  # Remove helper field
            leaderboard.append(student)
        
        return leaderboard