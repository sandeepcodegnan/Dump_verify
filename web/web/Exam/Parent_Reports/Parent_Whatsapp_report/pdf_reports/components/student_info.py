from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles

def create_student_info_section(student_data, period_id, batch_name):
    """Create student info section"""
    styles = get_styles()
    story = []
    
    story.append(Spacer(1, 0.7*inch))

    # Clean batch name
    display_batch = batch_name.split("_")[0] if "_" in batch_name else batch_name
    
    info_rows = [
        ['Student', (student_data.get('name') or 'Unknown').strip()],
        ['Period', str(period_id)],
        ['Batch', display_batch]
    ]
    
    info_table = Table(
        [[
            Paragraph(label, styles['InfoLabel']),
            Paragraph(':', styles['InfoLabel']),
            Paragraph(value, styles['InfoValue'])
        ] for label, value in info_rows],
        colWidths=[1*inch, 0.2*inch, 3*inch]
    )
    
    info_table.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),2),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE')
    ]))
    info_table.hAlign = 'LEFT'
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))

    # Divider
    divider = Table([['']], colWidths=[7.5*inch])
    divider.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,-1),1,colors.lightgrey)]))
    story.append(divider)
    story.append(Spacer(1, 0.09*inch))
    
    return story