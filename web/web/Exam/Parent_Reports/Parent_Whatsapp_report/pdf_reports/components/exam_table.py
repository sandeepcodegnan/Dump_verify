from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles

def create_exam_table(student_data):
    """Create exam table"""
    
    styles = get_styles()
    story = []
    
    if "dailyExam" not in student_data:
        return story
    story.append(Spacer(1, 0.2*inch))   
    story.append(Paragraph("Exam Reports", styles['SectionTitle']))
    exams = student_data['dailyExam']
    
    # Process exam data

    # Header
    exam_data = [[
        Paragraph(c, styles["TableHeader"])
        for c in ("Exam Name", "Attempted", "Subjects", "Marks", "Total Marks", "Percentage")
    ]]
    span_cmds = []
    row_idx = 1

    # Sort exams properly - handle different naming patterns
    def sort_exam_key(exam_name):
        try:
            if "-" in exam_name:
                return int(exam_name.split("-")[-1])
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    for exam_name in sorted(exams.keys(), key=sort_exam_key):
        ed = exams[exam_name]

        overall_max = ed.get("totalMarks", {}).get("maxScore", ed.get("totalMarks", 0))
        pct = f"{ed.get('percentage',0)}%"
        subs = [k for k in ed if k not in ("totalMarks","percentage","status")]


        attempted_symbol = "✔" if ed.get("status")=="attempted" else "✘"

        first = True
        for subj in sorted(subs):
            name_cell = Paragraph(exam_name, styles["TableBodyLeft"]) if first else ""
            attempt_cell = Paragraph(attempted_symbol, styles["CellCenter"]) if first else ""
            first = False

            obtained = ed[subj].get("score", 0)
            sub_max = ed[subj].get("maxScore", overall_max)
            marks_cell = f"{obtained}/{sub_max}"

            total_obj = ed.get("totalMarks", {})
            total_score = total_obj.get("score", overall_max)
            total_max = total_obj.get("maxScore", overall_max)
            total_cell = f"{total_score}/{total_max}"

            exam_data.append([
                name_cell,
                attempt_cell,
                Paragraph(subj,styles["TableBodyLeft"]),
                marks_cell,
                total_cell,
                pct
            ])

        # Span cells only if multiple subjects
        if len(subs) > 1:
            span_cmds.append(("SPAN", (0, row_idx), (0, row_idx + len(subs)-1)))
            span_cmds.append(("SPAN", (1, row_idx), (1, row_idx + len(subs)-1)))
            span_cmds.append(("SPAN", (4, row_idx), (4, row_idx + len(subs)-1)))
            span_cmds.append(("SPAN", (5, row_idx), (5, row_idx + len(subs)-1)))
        row_idx += len(subs)

    exam_tbl = Table(
        exam_data,
        colWidths=[1.9*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch]
    )

    base_exam_style = [
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#001c80')),
        ('TEXTCOLOR',  (0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.HexColor('#dde3e8')),
        ('BOX', (0,0),(-1,-1),1,colors.HexColor('#dde3e8')),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('ALIGN',(0,1),(0,-1),'LEFT'),
        ('ALIGN',(3,0),(3,-1),'CENTER'),
    ]
    
    # Add span commands to base style
    exam_style = TableStyle(base_exam_style + span_cmds)

    # Stripe rows
    for r in range(1, len(exam_data)):
        if r % 2 == 0:
            exam_style.add('BACKGROUND', (2, r), (2, r), colors.HexColor('#f2f5fc'))
            exam_style.add('BACKGROUND', (3, r), (3, r), colors.HexColor('#f2f5fc'))
            
    # Align merged columns
    for col in (0, 1, 4, 5):
        exam_style.add('ALIGN',  (col, 1), (col, -1), 'CENTER')
        exam_style.add('VALIGN', (col, 1), (col, -1), 'MIDDLE')

    exam_tbl.setStyle(exam_style)
    story.append(exam_tbl)
    
    # Legend
    story.append(Spacer(1, 0.2*inch))
    legend = [[
        Paragraph("Note:", styles['InfoLabel']),
        Paragraph("✔ = Attempted", styles['TableBodyLeft']),
        Paragraph("✘ = Not attempted", styles['TableBodyLeft'])
    ]]
    legend_tbl = Table(legend, colWidths=[0.6*inch, 1.5*inch, 1.5*inch])
    legend_tbl.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('ALIGN',        (0,0),(-1,-1),'LEFT'),
    ]))
    story.append(legend_tbl)
    
    return story