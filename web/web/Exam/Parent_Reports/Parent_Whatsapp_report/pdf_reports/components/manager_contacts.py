from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from web.Exam.exam_central_db import db, get_db
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles
import time
import random

def create_manager_contacts_table(location):
    """Create manager contacts table"""
    styles = get_styles()
    story = []
    
    if not location:
        return story
    
    student_location = location
    
    # Use a cache for manager contacts to avoid repeated DB queries
    # This is a simple in-memory cache that persists for the duration of the process
    if not hasattr(create_manager_contacts_table, "_manager_cache"):
        create_manager_contacts_table._manager_cache = {}
    
    # Check if we already have cached data for this location
    if student_location in create_manager_contacts_table._manager_cache:
        all_managers = create_manager_contacts_table._manager_cache[student_location]
    else:
        # Implement retry logic for MongoDB connection
        max_retries = 5  # Increased retries
        retry_count = 0
        all_managers = []
        
        while retry_count < max_retries:
            try:
                # Get a fresh DB connection to avoid connection pool issues
                current_db = get_db()
                
                # Add a small delay before query to prevent connection pool exhaustion
                # when multiple threads are accessing MongoDB simultaneously
                if retry_count > 0:
                    # Exponential backoff with jitter
                    backoff_time = min(2 ** retry_count + random.uniform(0, 1), 10)  # Cap at 10 seconds
                    time.sleep(backoff_time)
                else:
                    # Small initial delay even on first attempt to stagger concurrent requests
                    time.sleep(0.1 * (hash(student_location) % 10))  # 0-0.9 seconds based on location name
                
                # Fetch managers with timeout
                all_managers = list(current_db["Manager"].find(
                    {
                        "location": {"$regex": f"^{student_location}$", "$options": "i"},
                        "show_in_report": "True"
                    },
                    {"name": 1, "PhNumber": 1, "_id": 0}
                ).max_time_ms(5000))  # 5 second timeout
                
                # Cache the results
                create_manager_contacts_table._manager_cache[student_location] = all_managers
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    # Return empty list if all retries fail
                    return story
                # No need for additional sleep as we already have backoff above
    
    if not all_managers:
        return story
        
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Manager Contacts", styles['SectionTitle']))
    
    contact_data = [[
        Paragraph("Manager Name", styles['TableHeader']),
        Paragraph("Contact Number", styles['TableHeader'])
    ]]
    
    for manager in all_managers:
        contact_data.append([
            Paragraph(manager.get('name', 'N/A'), styles['TableBodyLeft']),
            Paragraph(manager.get('PhNumber', 'N/A'), styles['CellCenter'])
        ])
    
    contact_tbl = Table(contact_data, colWidths=[4.84*inch, 2.9*inch])
    contact_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001c80')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ]))
    story.append(contact_tbl)
    
    return story
    return story