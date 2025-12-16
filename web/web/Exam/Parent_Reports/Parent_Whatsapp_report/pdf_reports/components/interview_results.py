from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles
from web.Exam.exam_central_db import student_collection

def create_interview_results_section(student_data):
    """Create interview results section with URL"""
    styles = get_styles()
    story = []
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Interview Results", styles['SectionTitle']))
    story.append(Spacer(1, 0.1*inch))
    
    # Get email from student_login_details collection using 'id' field
    student_id = student_data.get('id')
    student_email = ''
    if student_id:
        student_record = student_collection.find_one({'id': student_id})
        if student_record:
            student_email = student_record.get('email', '')
        else:
            print(f"No student record found for id: {student_id}")
    else:
        print(f"No id found in student_data: {list(student_data.keys())}")
    
    interview_url = f"https://interview.cliqqai.com/user?page=profile&email={student_email}"
    
    if student_email:
        # Create a single paragraph with both label and link
        interview_text = f"<b><link href='{interview_url}'>Click Here for Your Interview Results</link></b>"
        story.append(Paragraph(interview_text, styles['InfoValue']))
    else:
        story.append(Paragraph("Interview performance tracking will be available once your profile is complete", styles['InfoValue']))
    
    return story