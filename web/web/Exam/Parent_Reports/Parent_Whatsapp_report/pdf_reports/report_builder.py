"""
report_builder.py

Module to assemble and merge multi-section PDF reports entirely in memory.
- Uses ReportLab for layout (SimpleDocTemplate).
- Merges sections with PyPDF2.PdfMerger.
"""
import io
from datetime import datetime
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from PyPDF2 import PdfMerger

# Import your layout components
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.header import draw_header
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.student_info import create_student_info_section
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.attendance_table import create_attendance_table
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.practice_attendance_table import create_practice_attendance_table
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.exam_table import create_exam_table
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.manager_contacts import create_manager_contacts_table
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.placement_table import create_placement_table
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.interview_results import create_interview_results_section
from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.components.styles import get_styles

# Get styles
styles = get_styles()
CENTERED_TITLE = styles['CenteredTitle']

def _create_section_pdf(story: List, header_title: str) -> bytes:
    """
    Render a single PDF section with a header, returning its bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.3 * inch,
        rightMargin=0.3 * inch,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
    )

    def _on_page(canvas, doc_obj):
        draw_header(canvas, doc_obj, header_title)

    doc.build(story, onFirstPage=_on_page)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_complete_report(
    student_data: dict,
    period_id: str,
    batch_name: str,
    is_monthly: bool = False
) -> bytes:
    """
    Build and merge all report sections for one student.

    Sections:
      1. Main report (student info, attendance, exams, contacts)
      2. Optional placement report

    Returns final PDF bytes.
    """
    merger = PdfMerger()
    try:
        # Main section
        story: List = []
        story.extend(create_student_info_section(student_data, period_id, batch_name))

        if is_monthly:
            # Add monthly title
            start = period_id.split("_to_")[0]
            month_year = datetime.strptime(start, "%Y-%m-%d").strftime("%B %Y")
            story.extend([
                Spacer(1, 0.04 * inch),
                Paragraph(f"Last Month Report ({month_year})", CENTERED_TITLE),
                Spacer(1, 0.09 * inch),
            ])
        story.extend(create_attendance_table(student_data, period_id))
        story.extend([
             Spacer(1, 0.09 * inch),
        ])
        story.extend(create_practice_attendance_table(student_data, period_id))
        story.extend(create_exam_table(student_data))
        story.extend(create_interview_results_section(student_data))
        story.extend(create_manager_contacts_table(student_data.get('location', batch_name)))

        main_pdf = _create_section_pdf(
            story,
            "Monthly Report" if is_monthly else "Weekly Report"
        )
        merger.append(io.BytesIO(main_pdf))

        # Placement section
        if student_data.get("placement"):
            placement_story = create_placement_table(student_data)
            placement_pdf = _create_section_pdf(placement_story, "Placement Report")
            merger.append(io.BytesIO(placement_pdf))

        # Write merged output
        output = io.BytesIO()
        merger.write(output)
        final_bytes = output.getvalue()
        output.close()
        return final_bytes

    finally:
        merger.close()
