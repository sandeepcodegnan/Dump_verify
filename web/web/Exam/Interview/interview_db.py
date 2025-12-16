"""Interview Database Operations"""
from typing import Dict, List
from web.Exam.exam_central_db import get_collection

def create_interview_record(interview_data: Dict, student_results: List[Dict]) -> str:
    """Create interview record following WhatsApp stats pattern"""
    interviews_collection = get_collection('interviews')
    batch = interview_data.get('batch')
    location = interview_data.get('location')
    
    interview_record = {
        'job_title': interview_data.get('job_title'),
        'week_range': f"{interview_data.get('weekRange', {}).get('startDate')}_{interview_data.get('weekRange', {}).get('endDate')}",
        'topics': interview_data.get('topics', ''),
        'application_link': interview_data.get('application_link', ''),
        'report_link': interview_data.get('report_link', ''),
        'student_ids': interview_data.get('studentIds', []),
        'created_at': interview_data.get('created_at')
    }
    
    # Update or create batch record - append to array like WhatsApp stats
    result = interviews_collection.update_one(
        {'batch': batch, 'location': location},
        {
            '$push': {'interviews': interview_record},
            '$setOnInsert': {'batch': batch, 'location': location}
        },
        upsert=True
    )
    
    return str(result.upserted_id) if result.upserted_id else 'updated'

def get_interviews_by_template_pattern(batch: str = None, week_num: str = None):
    """Get interviews matching job title template pattern from interviews array"""
    interviews_collection = get_collection('interviews')
    
    if batch:
        batch_doc = interviews_collection.find_one({"batch": batch})
        if not batch_doc or 'interviews' not in batch_doc:
            return []
        
        if week_num:
            target_job_title = f"{batch}-Week_{week_num}_interview"
            return [interview for interview in batch_doc['interviews'] 
                   if interview.get('job_title') == target_job_title]
        else:
            return batch_doc['interviews']
    
    return list(interviews_collection.find({}))
def get_next_week_number(batch: str) -> int:
    """Get next week number for a batch from interviews array"""
    interviews_collection = get_collection('interviews')
    
    # Find the batch document
    batch_doc = interviews_collection.find_one({"batch": batch})
    
    if not batch_doc or 'interviews' not in batch_doc:
        return 1
    
    # Find highest week number from interviews array
    max_week = 0
    for interview in batch_doc['interviews']:
        job_title = interview.get('job_title', '')
        if 'Week_' in job_title:
            try:
                week_num = int(job_title.split('Week_')[1].split('_')[0])
                max_week = max(max_week, week_num)
            except (IndexError, ValueError):
                continue
    
    return max_week + 1

def generate_personalized_interview_link(base_application_link: str, student_email: str) -> str:
    """Generate personalized interview link by appending student email"""
    if '?' in base_application_link:
        return f"{base_application_link}&emailid={student_email}"
    else:
        return f"{base_application_link}?emailid={student_email}"