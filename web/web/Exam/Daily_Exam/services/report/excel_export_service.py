"""Excel Export Service - Report Export Utilities (SoC)"""
from typing import Dict, Optional
from flask import Response
import pandas as pd
from io import BytesIO

class ExcelExportService:
    """Service for exporting report data to Excel format"""
    
    @staticmethod
    def export_batch_reports_to_excel(
        aggregated_data: Dict, 
        exam_metadata: Dict, 
        batch: str, 
        exam_type: str,
        exam_name: Optional[str] = None
    ) -> Response:
        """Convert batch reports data to Excel format and return Flask response"""
        
        # Convert to DataFrame for Excel export
        excel_data = []
        for report in aggregated_data.values():
            student = report.get("student", {})
            subjects = report.get("subjects", {})
            
            # Calculate total score from subjects
            total_score = report.get("overall_obtained_marks", 0)
            subject_scores = []
            for subject_name, subject_data in subjects.items():
                if isinstance(subject_data, dict):
                    score = subject_data.get("obtained_total_marks", 0)
                    subject_scores.append(f"{subject_name}: {score}")
            
            excel_data.append({
                "Student ID": student.get("studentId", ""),
                "Student Name": student.get("name", ""),
                "Phone Number": student.get("phNumber", ""),
                "Attempted": "Yes" if report.get("attempted") else "No",
                "Total Score": total_score,
                "Subject Scores": "; ".join(subject_scores)
            })
        
        # Create DataFrame
        df = pd.DataFrame(excel_data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Batch Reports', index=False)
        
        output.seek(0)
        
        # Generate filename
        filename = f"batch_reports_{batch}_{exam_type}"
        if exam_name:
            filename += f"_{exam_name}"
        filename += ".xlsx"
        
        # Create response with proper headers for download
        response = Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'Cache-Control': 'no-cache',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Expose-Headers': 'Content-Disposition'
            }
        )
        
        return response