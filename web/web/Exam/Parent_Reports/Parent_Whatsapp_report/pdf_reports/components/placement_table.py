from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles

def create_placement_table(student_data):
    """Create placement table"""
    styles = get_styles()
    story = []
    
    if "placement" not in student_data:
        return story
        
    story.append(Spacer(1, 0.7*inch))
    story.append(Paragraph("Placement Reports", styles['SectionTitle']))
    placement = student_data['placement']
    
    # Determine period label based on report type
    from datetime import datetime
    period_jobs = placement.get('period_jobs', 0)
    
    if period_jobs <= 10:  # Weekly report
        period_label = "This Week"
    else:  # Monthly report - show previous month name
        # Get previous month name
        from datetime import timedelta
        prev_month = datetime.now() - timedelta(days=30)
        month_name = prev_month.strftime("%B")
        period_label = f"{month_name} Month"
    
    # Single table with columns (period first, total last)
    placement_data = [[
        Paragraph("Metric", styles['TableHeader']),
        Paragraph(period_label, styles['TableHeader']),
        Paragraph("Total<br/><font size=8>(Since Batch Start)</font>", styles['TableHeader'])
    ]]
    
    placement_rows = [
        ["Jobs Posted", str(placement.get('period_jobs', 0)), str(placement.get('total_jobs', 0))],
        ["Jobs Eligible", str(placement.get('period_eligible', 0)), str(placement.get('eligible_jobs', 0))],
        ["Jobs Applied", str(placement.get('period_applied', 0)), str(placement.get('applied_jobs', 0))]
    ]
    
    for metric, period, total in placement_rows:
        placement_data.append([
            Paragraph(metric, styles['TableBodyLeft']),
            Paragraph(period, styles['CellCenter']),
            Paragraph(total, styles['CellCenter'])
        ])
    
    placement_tbl = Table(placement_data, colWidths=[3.5*inch, 2.12*inch, 2.12*inch])
    placement_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001c80')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # Center and middle align headers
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ]))
    story.append(placement_tbl)
    story.append(Spacer(1, 0.3*inch))
    
    return story