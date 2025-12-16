import io
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Spacer
from components.header import add_header_image
from components.content import add_certificate_title, add_certificate_content
from components.signature import add_date_and_signature, add_signature_image, add_stamp_image
from components.footer import add_footer_image

def create_certificate_pdf(student_data, output_path=None):
    """
    Create a complete certificate PDF for a student
    
    Args:
        student_data (dict): Student information containing:
            - name: Student name
            - role: Course/role completed
            - duration: Course duration
            - technologies: Technologies learned
            - project: Project completed
            - location: Branch location
            - trainer: Trainer name
            - print_date: Certificate date
        output_path (str): Path to save the PDF file
    
    Returns:
        bytes: PDF content as bytes if output_path is None
        str: File path if output_path is provided
    """
    
    # Create buffer for PDF content
    if output_path:
        # Save to file
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=0.64*inch,
            rightMargin=0.64*inch,
            topMargin=0.64*inch,
            bottomMargin=0.64*inch
        )
    else:
        # Create in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.64*inch,
            rightMargin=0.64*inch,
            topMargin=0.64*inch,
            bottomMargin=0.64*inch
        )
    
    # Build the story (content)
    story = []
    
    # Add header image
    add_header_image(story)
    
    # Add date at top right (matching DOCX)
    print_date = student_data.get('print_date', '')
    location = student_data.get('location', '')
    if print_date and location:
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        
        date_table = Table([["", print_date], ["", location]], colWidths=[4.72*inch, 2*inch], rowHeights=[0.2*inch, 0.2*inch])
        date_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 1), 'CENTER'),
            ('FONTNAME', (1, 0), (1, 1), 'Times-Bold'),
            ('FONTSIZE', (1, 0), (1, 1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (1, 0), (1, 1), 2),
            ('BOTTOMPADDING', (1, 0), (1, 1), 2),
        ]))
        story.append(date_table)
        story.append(Spacer(1, 0.02*inch))
    
    # Add certificate title
    add_certificate_title(story)
    story.append(Spacer(1, 0.1*inch))
    
    # Add main certificate content
    add_certificate_content(story, student_data)
    
    # Add date and signature section
    add_date_and_signature(story, student_data)
    
    # Add signature image
    add_signature_image(story)
    
    # Add stamp image
    add_stamp_image(story)
    
    # Add footer image
    add_footer_image(story)
    
    # Build the PDF
    doc.build(story)
    
    if output_path:
        return output_path
    else:
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

def create_batch_certificates(students_data, output_directory):
    """
    Create certificates for multiple students
    
    Args:
        students_data (list): List of student data dictionaries
        output_directory (str): Directory to save PDF files
    
    Returns:
        list: List of created file paths
    """
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    created_files = []
    
    for student_data in students_data:
        student_name = student_data.get('name', 'Unknown').strip()
        # Clean filename
        safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_path = os.path.join(output_directory, f"{safe_name}.pdf")
        
        try:
            create_certificate_pdf(student_data, output_path)
            created_files.append(output_path)
            print(f"Created certificate for: {student_name}")
        except Exception as e:
            print(f"Error creating certificate for {student_name}: {e}")
    
    return created_files