"""Interview Service - Business Logic Layer"""
from datetime import datetime, timedelta
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.utils.time.week_utils import get_week_range
from web.Exam.Interview.external.interview_system_client import InterviewSystemClient
from web.Exam.Interview.external.ses_client import SESClient
from web.Exam.Interview.interview_db import get_next_week_number, create_interview_record
from web.Exam.Interview.config.interview_config import InterviewConfig
from web.Exam.exam_central_db import student_collection, get_collection
from web.Exam.Daily_Exam.config.settings import NON_TECH_SUBJECTS


class InterviewService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
        self.interview_system_client = InterviewSystemClient()
        self.ses_client = SESClient()
    
    def get_curriculum_data(self, batch, location):
        """Get interview data for current week range and create interview job"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        try:
            start_date, end_date = get_week_range(current_date)
        except Exception as e:
            raise ValueError(f"Date processing error: {str(e)}")
        
        # Get week range curriculum data
        result = self._get_interview_curriculum_data(start_date, end_date, batch, location)
        
        # Auto-create interview system job (only once per week)
        if result.get('success') and result.get('data'):
            week_num = get_next_week_number(batch)
            
            # Check if already created for this week range
            interviews_collection = get_collection('interviews')
            week_range_str = f"{start_date}_{end_date}"
            
            batch_doc = interviews_collection.find_one({
                'batch': batch,
                'location': location
            })
            
            # Check if any interview has this date range
            week_exists = False
            if batch_doc and 'interviews' in batch_doc:
                for interview in batch_doc['interviews']:
                    if interview.get('week_range') == week_range_str:
                        week_exists = True
                        break
            
            existing = week_exists
            
            if not existing:
                interview_response = self._create_interview_system_job(batch, result['data'], week_num, location)
                if interview_response:
                    result['interview_system'] = interview_response
                
                # Send notifications and store
                student_ids = self._get_eligible_students(batch, location)
                if student_ids:
                    deadline_date = (datetime.now() + timedelta(days=1)).strftime('%d-%m-%Y, %I:%M %p')
                    notification_data = {
                        "job_title": f"{batch}-Week_{week_num}_interview",
                        "batch": batch,
                        "location": location,
                        "topics": "; ".join([f"{subj}: {data['topics']}" for subj, data in result['data'].items()]),
                        "weekRange": result.get('weekRange', {}),
                        "studentIds": student_ids,
                        "application_link": interview_response.get('application_link', ''),
                        "report_link": interview_response.get('report_link', ''),
                        "deadline_date": deadline_date,
                        "created_at": datetime.now().isoformat()
                    }
                    ses_response = self.ses_client.send_interview_notifications(notification_data)
                    total_students = ses_response.get('total_students', len(student_ids))
                    
                    record_id = create_interview_record(notification_data, ses_response.get('results', []))
                    
                    return {'message': f'Interview scheduled with {total_students} students {batch}'}
            else:
                return {'status': 'already_exists', 'message': f'Interview already exists for this week batch {batch}'}
        
        return result
    

    
    def _get_interview_curriculum_data(self, start_date, end_date, batch, location):
        """Get curriculum data for interview (week range without date field)"""
        try:
            curriculum_repo = self.repo_factory.get_curriculum_repo()
            subj_docs = curriculum_repo.get_curriculum_data_range(start_date, end_date, batch, location)
            
            if not subj_docs:
                raise ValueError("Sorry - Nothing has been scheduled for this week.")
            
            # Process subjects for interview (no breakdown, no tags, no date) - exclude non-technical subjects
            data = {}
            for sd in subj_docs:
                subject = sd["subject"]
                if subject.lower() not in NON_TECH_SUBJECTS:
                    data[subject] = {
                        "topics": ", ".join(sd["topics"]),
                        "subtitles": sd["subtitles"]
                    }
            
            return {
                "success": True,
                "data": data,
                "weekRange": {"startDate": start_date, "endDate": end_date}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_eligible_students(self, batch, location):
        """Get eligible students for interviews"""
        try:
            students = student_collection.find(
                {"BatchNo": batch, "location": location, "placed": {"$ne": True}},
                {"id": 1}
            )
            student_ids = [stu["id"] for stu in students]
            
            if not student_ids:
                raise ValueError("No eligible students found for interview")
            
            return student_ids
        except Exception as e:
            raise ValueError(f"Error getting eligible students: {str(e)}")
    
    def _create_interview_system_job(self, batch, curriculum_data, week_num, location):
        """Create single interview job combining all subjects"""
        try:
            if not batch or not curriculum_data:
                return None
            
            # Get assigned manager from database based on location
            assigned_manager = InterviewConfig.get_assigned_manager(location)
            
            # Combine all subjects into one job
            all_topics = []
            all_subtitles = []
            
            for subject, data in curriculum_data.items():
                if not isinstance(data, dict):
                    continue
                    
                topics = data.get('topics', '')
                subtitles = data.get('subtitles', [])
                
                if topics:
                    all_topics.append(f"{subject}: {topics}")
                if subtitles:
                    all_subtitles.extend(subtitles)
            
            if not all_topics and not all_subtitles:
                return None
            
            # Create single job with all subjects combined
            combined_topics = "; ".join(all_topics)
            
            system_result = self.interview_system_client.create_interview_job(
                batch=batch,
                topics=combined_topics,
                subtitles=all_subtitles,
                week_num=week_num,
                assigned=assigned_manager
            )
            
            if system_result.get('success'):
                return system_result.get('data', {})
            else:
                return None
                    
        except Exception:
            return None