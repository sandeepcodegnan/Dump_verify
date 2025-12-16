"""Check Exam Status Service - Verify exam scheduling conflicts"""
from typing import Dict
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.related.active_batches import get_batches_collection
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.utils.pagination.pagination_utils import build_paginated_response
from web.Exam.Daily_Exam.config.settings import EXCLUDED_EXAM_SUBJECTS

class CheckExamStatusService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
        self.batches_coll = get_batches_collection()
    
    def check_batches_status(self, exam_type: str, location: str, date: str, page: int = 1, limit: int = 10) -> Dict:
        exam_type = ExamValidationService.validate_exam_type(exam_type)
        
        # Get active batches for location
        query = {"Status": "Active", "location": {"$regex": f"^{location}$", "$options": "i"}}
        active_batches = list(self.batches_coll.find(query, {"Batch": 1, "_id": 0}))
        
        if not active_batches:
            return build_paginated_response(True, [], page, limit)
        
        curriculum_repo = self.repo_factory.get_curriculum_repo()
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
        
        pending_batches = []
        conducted_batches = []
        no_curriculum_batches = []
        
        for batch_doc in active_batches:
            batch = batch_doc["Batch"]
            
            # Check if curriculum exists for this batch and date
            curriculum_data = curriculum_repo.get_curriculum_data(date, batch, location)
            if curriculum_data:
                # Filter out excluded subjects
                filtered_data = [doc for doc in curriculum_data if doc["subject"].lower() not in EXCLUDED_EXAM_SUBJECTS]
                if not filtered_data:
                    continue
                subjects = [doc["subject"] for doc in filtered_data]
                exists = exam_repo.exists_for_date(batch, location, date)
                
                if exists:
                    conducted_batches.append({"batch": batch, "subjects": subjects, "status": True, "message": "Exam already conducted"})
                else:
                    pending_batches.append({"batch": batch, "subjects": subjects, "status": False, "message": "Need to conduct exam"})
            else:
                no_curriculum_batches.append({"batch": batch, "status": None, "message": "No curriculum scheduled"})
        
        # Order: pending first, then conducted, then no curriculum
        all_batches = pending_batches + conducted_batches + no_curriculum_batches
        
        # Add statistics
        stats = {
            "total_active_batches": len(active_batches),
            "need_to_conduct": len(pending_batches),
            "already_conducted": len(conducted_batches),
            "no_curriculum": len(no_curriculum_batches)
        }
        
        return build_paginated_response(True, all_batches, page, limit, {"stats": stats})
    
    def get_subjects_for_batch(self, exam_type: str, location: str, date: str, batch: str):
        exam_type = ExamValidationService.validate_exam_type(exam_type)
        curriculum_repo = self.repo_factory.get_curriculum_repo()
        
        # Get curriculum data for specific batch
        curriculum_data = curriculum_repo.get_curriculum_data(date, batch, location)
        if not curriculum_data:
            return {"success": False, "message": "No curriculum scheduled for this batch"}
        
        # Filter out excluded subjects
        filtered_data = [doc for doc in curriculum_data if doc["subject"].lower() not in EXCLUDED_EXAM_SUBJECTS]
        subjects = [doc["subject"] for doc in filtered_data]
        
        return {"success": True, "subjects": subjects}
