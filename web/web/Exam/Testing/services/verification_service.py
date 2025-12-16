"""
Verification Service
Business logic for question verification and progress tracking
"""
from typing import Dict, List
from bson import ObjectId
from web.Exam.Testing.services.base_service import BaseService
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class VerificationService(BaseService):
    """Service for verification operations"""
    
    def __init__(self):
        super().__init__()
        self._ensure_verification_index()
    
    def verify_question(self, intern_id: str, question_id: str, question_type: str, 
                       subject: str, tag: str, verified: bool = True, 
                       source_code: str = None) -> Dict:
        """Mark question as verified/unverified"""
        qid = InputValidator.validate_object_id(question_id)
        
        update_fields = {
            "verified": verified,
            "verifiedAt": self.get_current_utc()
        }
        
        if source_code and question_type in ["code_test", "code_codeplayground_test"]:
            update_fields["sourceCode"] = source_code
        elif source_code and question_type in ["query_test", "query_codeplayground_test"]:
            update_fields["query"] = source_code
        
        # Update verification record
        self.update_one(
            self.collections["verification"],
            {"id": intern_id, "questionId": qid},
            {"$set": update_fields}
        )
        
        # Check if topic should be marked complete
        if verified:
            self._check_topic_completion(intern_id, subject, tag)
        
        return {
            "internId": intern_id,
            "questionId": question_id,
            "questionType": question_type,
            "subject": subject,
            "tag": tag,
            "verified": verified,
            "verifiedAt": update_fields["verifiedAt"].isoformat() + "Z"
        }
    
    def get_verification_history(self, intern_id: str, subject: str = None, 
                               question_type: str = None) -> List[Dict]:
        """Get verification history for intern (for internal lookup)"""
        query = {"id": intern_id}
        if subject:
            query["subject"] = subject.lower()
        if question_type:
            query["questionType"] = question_type.lower()
        
        records = self.find_many(self.collections["verification"], query, {"_id": 0})
        
        formatted_records = []
        for record in records:
            formatted_record = {
                "internId": record["id"],
                "questionId": str(record["questionId"]),
                "questionType": record.get("questionType"),
                "subject": record.get("subject"),
                "tag": record.get("tag"),
                "verified": record.get("verified", False)
            }
            
            # Add appropriate code field based on question type
            if record.get("questionType") in ["query_test", "query_codeplayground_test"]:
                formatted_record["query"] = record.get("query")
            else:
                formatted_record["sourceCode"] = record.get("sourceCode")
                
            formatted_records.append(formatted_record)
        
        return formatted_records
    
    def create_verification_record(self, intern_id: str, question_id: ObjectId, 
                                 question_type: str, subject: str, tag: str) -> None:
        """Create initial verification record"""
        record = {
            "id": intern_id,
            "questionId": question_id,
            "questionType": question_type,
            "subject": subject.lower(),
            "tag": tag.lower(),
            "verified": False,
            "createdAt": self.get_current_utc()
        }
        
        self.update_one(
            self.collections["verification"],
            {"id": intern_id, "questionId": question_id},
            {"$setOnInsert": record},
            upsert=True
        )
    
    def _check_topic_completion(self, intern_id: str, subject: str, tag: str) -> None:
        """Check if all questions for topic are verified and mark curriculum complete"""
        # Count total questions for this tag
        total_questions = self._count_total_questions(subject, tag)
        
        # Count verified questions
        verified_count = self.count_documents(
            self.collections["verification"],
            {
                "id": intern_id,
                "subject": subject.lower(),
                "tag": tag.lower(),
                "verified": True
            }
        )
        
        # Mark curriculum topic complete if all verified
        if total_questions > 0 and verified_count >= total_questions:
            self._mark_curriculum_topic_done(intern_id, subject, tag)
    
    def _count_total_questions(self, subject: str, tag: str) -> int:
        """Count total questions for subject and tag"""
        total = 0
        subject_lower = subject.lower()
        
        # Count across all question type collections
        for collection_name in self.db.list_collection_names():
            if collection_name.startswith(f"{subject_lower}_") and collection_name.endswith("_test"):
                count = self.count_documents(collection_name, {"Tags": tag.lower()})
                total += count
        
        return total
    
    def _mark_curriculum_topic_done(self, intern_id: str, subject: str, tag: str) -> None:
        """Mark curriculum subtopic as completed"""
        tester = self.find_one(
            self.collections["testers"],
            {"id": intern_id},
            {"curriculumTable": 1}
        )
        
        if not tester:
            return
        
        curriculum_table = tester.get("curriculumTable", {})
        subject_key = next((k for k in curriculum_table if k.lower() == subject.lower()), None)
        
        if not subject_key:
            return
        
        # Find and update the subtopic
        for block_id, block in curriculum_table[subject_key].items():
            for idx, subtopic in enumerate(block.get("SubTopics", [])):
                if subtopic.get("tag") == tag.lower():
                    path = f"curriculumTable.{subject_key}.{block_id}.SubTopics.{idx}.status"
                    self.update_one(
                        self.collections["testers"],
                        {"id": intern_id},
                        {"$set": {path: True}}
                    )
                    return
    
    def _ensure_verification_index(self) -> None:
        """Ensure verification collection has proper index"""
        try:
            self.create_index(
                self.collections["verification"],
                [("id", 1), ("questionId", 1)],
                unique=True
            )
        except Exception:
            pass  # Index might already exist