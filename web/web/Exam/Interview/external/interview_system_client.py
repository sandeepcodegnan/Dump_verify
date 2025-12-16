"""Interview System API Client"""
import requests
from typing import Dict, Any
from web.Exam.Interview.config.interview_config import InterviewConfig

class InterviewSystemClient:
    def __init__(self):
        InterviewConfig.validate_config()
        self.base_url = InterviewConfig.INTERVIEW_API_BASE_URL
        self.timeout = InterviewConfig.INTERVIEW_API_TIMEOUT
        self.headers = InterviewConfig.get_api_headers()
    
    def create_interview_job(self, batch: str, topics: str, subtitles: list, assigned: str = "sandeep", week_num: int = 1) -> Dict[str, Any]:
        """Create interview job in interview system"""
        try:
            # Validate inputs
            if not batch or not isinstance(batch, str):
                return {"success": False, "error": "Invalid batch parameter"}
            
            # Combine topics and subtitles
            subtitles_str = ""
            if isinstance(subtitles, list) and subtitles:
                subtitles_str = ", ".join(str(item) for item in subtitles if item)
            
            if topics and subtitles_str:
                job_description = f"{topics}: {subtitles_str}"
            elif topics:
                job_description = topics
            elif subtitles_str:
                job_description = subtitles_str
            else:
                job_description = "Interview topics"
            
            payload = {
                "job_title": InterviewConfig.INTERVIEW_JOB_TITLE_TEMPLATE.format(batch=batch, week_num=week_num),
                "assigned": assigned or "sandeep",
                "job_description": job_description.strip()
            }
            
            url = f"{self.base_url}{InterviewConfig.INTERVIEW_ENDPOINT}"
            response = requests.post(url, headers=self.headers, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False, 
                    "error": f"API Error: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
