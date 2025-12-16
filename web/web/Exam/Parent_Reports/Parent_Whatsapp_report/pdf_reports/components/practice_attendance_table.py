from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles

def create_practice_attendance_table(student_data, period_id):
    """Create practice attendance table - week-wise for monthly, single for weekly"""
    
    styles = get_styles()
    story = []
    if "practiceAttendance" not in student_data or not student_data['practiceAttendance']:
        return story
    
    att = student_data['practiceAttendance']
    start_str, end_str = period_id.split("_to_")
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days + 1
    
    if delta_days > 7:  # Monthly - create week-wise tables
        story.append(Paragraph("Practice Attendance Reports (Week-wise)", styles['SectionTitle']))
        
        # Group dates by weeks
        weekly_groups = group_practice_attendance_by_weeks(att, start_dt, end_dt)
        
        for week_num, week_dates in weekly_groups.items():
            story.append(Paragraph(f"Week {week_num}", styles['SectionTitle']))
            
            # Create table for this week
            week_table = create_week_practice_attendance_table(week_dates, att, styles)
            story.append(week_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Add overall percentage for monthly
        overall_pct = att.get('overallPercentage', 0)
        overall_data = [[
            Paragraph('Overall Practice Attendance:', styles['InfoLabel']), 
            Paragraph(f'{overall_pct}%', styles['InfoValue'])
        ]]
        overall_tbl = Table(overall_data, colWidths=[3*inch, 1*inch])
        overall_tbl.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(overall_tbl)
        
        # Add legend
        legend_data = [[
            Paragraph('Note:', styles['InfoLabel']),
            Paragraph('✔ = Present', styles['TableBodyLeft']),
            Paragraph('✘ = Absent', styles['TableBodyLeft']),
            Paragraph('– = No practice/Month end', styles['TableBodyLeft'])
        ]]
        legend_tbl = Table(legend_data, colWidths=[0.6*inch, 1.5*inch, 1.5*inch, 2.0*inch])
        legend_tbl.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(legend_tbl)
        story.append(Spacer(1, 0.2*inch))
        
    else:  # Weekly - single table
        story.append(Paragraph("Practice Attendance Reports", styles['SectionTitle']))
        
        # Build dates for weekly
        delta_days = min(delta_days, 6)
        dates = [(start_dt + timedelta(days=off)).strftime("%Y-%m-%d") for off in range(delta_days)]
        
        # Create single weekly table
        weekly_table = create_single_practice_attendance_table(dates, att, styles)
        story.append(weekly_table)
        
        # Add overall percentage for weekly
        overall_pct = att.get('overallPercentage', 0)
        overall_data = [[
            Paragraph('Overall Practice Attendance:', styles['InfoLabel']), 
            Paragraph(f'{overall_pct}%', styles['InfoValue'])
        ]]
        overall_tbl = Table(overall_data, colWidths=[3*inch, 1*inch])
        overall_tbl.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(overall_tbl)
        
        # Legend
        legend_data = [[
            Paragraph('Note:', styles['InfoLabel']),
            Paragraph('✔ = Present', styles['TableBodyLeft']),
            Paragraph('✘ = Absent', styles['TableBodyLeft']),
            Paragraph('– = No practice', styles['TableBodyLeft'])
        ]]
        legend_tbl = Table(legend_data, colWidths=[0.6*inch, 1.8*inch, 1.8*inch, 1.8*inch])
        legend_tbl.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(legend_tbl)
        story.append(Spacer(1, 0.2*inch))
    
    return story

def group_practice_attendance_by_weeks(att, start_dt, end_dt):
    """Group practice attendance dates by fixed Monday-Saturday weeks"""
    weekly_groups = {}
    
    # Find the Monday of the week containing start_dt
    days_from_monday = start_dt.weekday()
    week_start = start_dt - timedelta(days=days_from_monday)
    
    week_num = 1
    current_week_start = week_start
    
    while current_week_start <= end_dt:
        week_dates = []
        
        # Generate Monday to Saturday for this week
        for day_offset in range(6):  # 0=Monday, 5=Saturday
            current_date = current_week_start + timedelta(days=day_offset)
            
            if current_date < start_dt or current_date > end_dt:
                week_dates.append("-")  # Before month start or after month end
            else:
                week_dates.append(current_date.strftime("%Y-%m-%d"))
        
        weekly_groups[week_num] = week_dates
        week_num += 1
        current_week_start += timedelta(days=7)  # Next Monday
    
    return weekly_groups

def create_week_practice_attendance_table(week_dates, att, styles):
    """Create practice attendance table for a specific week with fixed Monday-Saturday structure"""
    # Week dates already contain 6 elements (Monday-Saturday) with "-" for empty days
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    # Create header with dates only
    header_dates = []
    for date in week_dates:
        if date == "-":
            header_dates.append("-")
        else:
            header_dates.append(date)  # Full date format YYYY-MM-DD
    
    header = ["Courses"] + header_dates + ["Week %"]
    header_row = [Paragraph(col, styles['TableHeader']) for col in header]
    table_data = [header_row]
    
    # Process each course
    for course_name, course_data in att.items():
        if isinstance(course_data, dict) and course_name not in ['overallPercentage']:
            row = [Paragraph(course_name, styles['TableBodyLeft'])]
            
            present_count = 0
            total_days = 0
            
            for date in week_dates:
                if date == "-":
                    row.append("-")
                else:
                    status = course_data.get(date, "")
                    if status == "present":
                        row.append("✔")
                        present_count += 1
                        total_days += 1
                    elif status == "absent":
                        row.append("✘")
                        total_days += 1
                    else:
                        row.append("-")
            
            week_pct = round((present_count / total_days) * 100) if total_days > 0 else 0
            row.append(f"{week_pct}%")
            table_data.append(row)
    
    table = Table(table_data, colWidths=[1.53*inch] + [0.9*inch]*6 + [0.83*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001c80')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ]))
    
    return table

def create_single_practice_attendance_table(dates, att, styles):
    """Create single practice attendance table for weekly reports"""
    header = ["Courses"] + dates + ["Overall %"]
    header_row = [Paragraph(col, styles['TableHeader']) for col in header]
    attendance_data = [header_row]
    
    total_pct = 0
    course_items = [(course, data) for course, data in att.items() if isinstance(data, dict) and course != 'overallPercentage']
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    for course_name, data in course_items:
        pct = data.get("percentage", 0) if isinstance(data, dict) else 0
        total_pct += pct
        
        row = [Paragraph(str(course_name), styles['TableBodyLeft'])]
        for d in dates:
            v = data.get(d) if isinstance(data, dict) else None
            row.append("✔" if v == "present" else "✘" if v == "absent" else "–" if d < today_str else "")
        row.append(f"{pct}%")
        attendance_data.append(row)

    
    att_tbl = Table(attendance_data, colWidths=[1.5*inch] + [0.9*inch]*len(dates) + [0.8*inch])
    att_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#001c80')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dde3e8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    # Stripe rows
    for ri in range(1, len(attendance_data)):
        if ri % 2 == 0:
            att_tbl.setStyle(TableStyle([('BACKGROUND', (0, ri), (-1, ri), colors.HexColor('#f2f5fc'))]))
    
    return att_tbl