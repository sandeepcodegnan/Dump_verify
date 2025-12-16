import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer, Image
from reportlab.platypus.doctemplate import PageTemplate
from .components.content import add_certificate_title, add_certificate_content
from .components.signature import add_date_and_signature, add_signature_image, add_stamp_image, add_signature_and_stamp_images

def header_footer_on_page(canvas, doc):
    """Add header and footer to each page with white background"""
    
    # Set white background for entire page
    canvas.setFillColorRGB(1, 1, 1)  # White background
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    
    # Header - full page width
    header_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asserts', 'head.png')
    if os.path.exists(header_path):
        canvas.drawImage(header_path, 0, A4[1] - 1.5*inch, width=A4[0], height=1.2*inch)
    
    # Footer - ensure white background first, then draw footer image
    canvas.setFillColorRGB(1, 1, 1)  # White background for footer area
    canvas.rect(0, 0, A4[0], 1.2*inch, fill=1, stroke=0)  # White rectangle
    
    footer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asserts', 'footer.png')
    if os.path.exists(footer_path):
        # Draw footer image with proper scaling and positioning
        try:
            canvas.drawImage(footer_path, 0, 0, width=A4[0], height=1.2*inch, preserveAspectRatio=True, mask='auto')
        except:
            # If there's any issue with the image, just keep white background
            pass

def create_certificate_pdf(student_data, output_path=None):
    """Create certificate with proper page headers/footers"""
    
    if output_path:
        doc = BaseDocTemplate(output_path, pagesize=A4)
    else:
        buffer = io.BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=A4)
    
    # Create frame for content (leaving space for header/footer)
    frame = Frame(
        0.64*inch, 1.4*inch,  # x, y (more space for footer)
        6.72*inch, 8.1*inch,  # width, height (adjusted for larger footer)
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0
    )
    
    # Create page template with header/footer
    template = PageTemplate(id='certificate', frames=[frame], onPage=header_footer_on_page)
    doc.addPageTemplates([template])
    
    # Build story
    story = []
    
    # Add date at top right
    print_date = student_data.get('print_date', '')
    location = student_data.get('location', '')
    if print_date and location:
        from reportlab.platypus import Table, TableStyle
        
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
        story.append(Spacer(1, 0.1*inch))
    
    # Add certificate content
    add_certificate_title(story)
    story.append(Spacer(1, 0.1*inch))
    add_certificate_content(story, student_data)
    add_date_and_signature(story, student_data)
    add_signature_and_stamp_images(story)
    
    # Build PDF
    doc.build(story)
    
    if output_path:
        return output_path
    else:
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes