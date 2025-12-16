"""Report Service - Business Logic Layer (SoC)"""
from typing import Dict, Optional
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.utils.analysis.analysis_utils import calculate_subject_scores
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.services.report.excel_export_service import ExcelExportService

class ReportService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def get_batch_reports(self, exam_type: str, batch: str, exam_name: Optional[str] = None, page: int = 1, limit: int = 50, search: Optional[str] = None, attempted: Optional[str] = None, sort_by: Optional[str] = None, sort_order: str = "asc") -> Dict:
        """Get batch reports with student details and subject-wise scores"""
        from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
        
        exam_type = ExamValidationService.validate_exam_type(exam_type)
        
        # Use optimized repo for Weekly/Monthly exams
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
        
        # Build match filter
        match_filter = {"batch": batch}
        if exam_name:
            match_filter["examName"] = exam_name
        
        # Get exam data with student lookup
        exams = exam_repo.get_batch_reports_data(match_filter, search, attempted, sort_by, sort_order)
        
        if not exams:
            msg = f"No exam records found for batch {batch}"
            if exam_name:
                msg += f" and examName {exam_name}"
            raise ValueError(msg)
        
        # Process and aggregate data
        aggregated_data, exam_metadata = self._process_exam_reports(exams)
        
        # Apply centralized pagination
        from web.Exam.Daily_Exam.utils.pagination.pagination_utils import build_paginated_response
        
        all_reports = list(aggregated_data.values())
        
        # Apply sorting based on parameters
        if sort_by == "score":
            reverse_order = sort_order.lower() == "desc"
            all_reports.sort(key=lambda x: x.get("overall_obtained_marks", 0), reverse=reverse_order)
        else:
            # Default sort by overall_obtained_marks (desc), then by attempted status (attempted first)
            all_reports.sort(key=lambda x: (x.get("overall_obtained_marks", 0), x.get("attempted", False)), reverse=True)
        additional_fields = {
            "batch": batch,
            "examDetails": exam_metadata
        }
        if exam_name:
            additional_fields["examName"] = exam_name
        
        response = build_paginated_response(
            success=True,
            data=all_reports,
            page=page,
            limit=limit,
            additional_fields=additional_fields
        )
        
        # Rename 'data' to 'reports' for consistency
        response["reports"] = response.pop("data")
        
        return sanitize_mongo_document(response)
    
    def _process_exam_reports(self, exams) -> Dict:
        """Process exam data into aggregated reports"""
        aggregated_data = {}
        exam_metadata = {}

        
        for exam in exams:
            student = exam.get("student")
            if not student:
                continue
                
            student_id = student.get("id")
            exam_name = exam.get("examName")
            
            if not student_id or not exam_name:
                continue
            
            # Store exam metadata once
            if not exam_metadata:
                exam_metadata = {
                    "startDate": exam.get("startDate"),
                    "totalExamTime": exam.get("totalExamTime"),
                    "batch": exam.get("batch"),
                    "location": exam.get("location")
                }
            
            comp_key = f"{student_id}_{exam_name}"
            if comp_key not in aggregated_data:
                aggregated_data[comp_key] = {
                    "student": {
                        "id": student.get("id"),
                        "name": student.get("name"),
                        "studentId": student.get("studentId"),
                        "phNumber": student.get("studentPhNumber")
                    },
                    "subjects": {},
                    "attempted": False
                }
            
            # Process subjects and scores using DRY utility
            try:
                paper = exam.get("paper", [])
                analysis = exam.get("analysis") or {}
                details = analysis.get("details", []) if isinstance(analysis, dict) else []
                subjects = exam.get("subjects", [])
                
                subjects_summary = calculate_subject_scores(paper, details, subjects)
                
                # Extract overall obtained marks
                overall_obtained = subjects_summary.pop("_overall_obtained", 0)
                
                aggregated_data[comp_key]["subjects"] = subjects_summary
                aggregated_data[comp_key]["overall_obtained_marks"] = overall_obtained
                
                # Use database attempt-status (defaults to false if not present)
                aggregated_data[comp_key]["attempted"] = exam.get("attempt-status", False)
                
            except Exception:
                # Fallback to empty subjects if processing fails
                aggregated_data[comp_key]["subjects"] = {}
                aggregated_data[comp_key]["attempted"] = False
        
        # Calculate attempted and not attempted counts
        attempted_count = sum(1 for report in aggregated_data.values() if report["attempted"])
        not_attempted_count = len(aggregated_data) - attempted_count
        
        # Add counts to exam metadata
        exam_metadata["attemptedCount"] = attempted_count
        exam_metadata["notAttemptedCount"] = not_attempted_count
        
        return aggregated_data, exam_metadata
    
    def export_batch_reports_excel(self, exam_type: str, batch: str, exam_name: Optional[str] = None, search: Optional[str] = None, attempted: Optional[str] = None, sort_by: Optional[str] = None, sort_order: str = "asc"):
        """Export batch reports to Excel format"""
        from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
        
        exam_type = ExamValidationService.validate_exam_type(exam_type)
        
        # Use optimized repo for Weekly/Monthly exams
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
        
        # Build match filter
        match_filter = {"batch": batch}
        if exam_name:
            match_filter["examName"] = exam_name
        
        # Get all exam data without pagination
        exams = exam_repo.get_batch_reports_data(match_filter, search, attempted, sort_by, sort_order)
        
        if not exams:
            msg = f"No exam records found for batch {batch}"
            if exam_name:
                msg += f" and examName {exam_name}"
            raise ValueError(msg)
        
        # Process and aggregate data
        aggregated_data, exam_metadata = self._process_exam_reports(exams)
        
        # Use Excel export service
        return ExcelExportService.export_batch_reports_to_excel(
            aggregated_data, exam_metadata, batch, exam_type, exam_name
        )
