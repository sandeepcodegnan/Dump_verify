"""
Tester Management Service
Business logic for tester CRUD operations and curriculum management
"""
import uuid
import bcrypt
from typing import Dict, List, Optional
from .base_service import BaseService
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError, DatabaseError

class TesterService(BaseService):
    """Service for tester management operations"""
    
    def create_tester(self, data: Dict) -> Dict:
        """Create new tester with curriculum"""
        # Validate required fields
        required = ["name", "email", "Designation"]
        InputValidator.validate_required_fields(data, required)
        
        email = data["email"].lower()
        
        # Check for existing email
        if self.find_one(self.collections["testers"], {"email": email}):
            raise ValidationError("Email already exists")
        
        # Generate tester data
        tester_id = str(uuid.uuid4())
        designation = data["Designation"]
        subjects = designation if isinstance(designation, list) else [designation]
        
        # Build curriculum table
        curriculum_table = self._build_curriculum_table(subjects)
        
        # Create tester document
        tester = {
            "id": tester_id,
            "timestamp": self.get_current_utc().isoformat(),
            "name": data["name"],
            "email": email,
            "password": self._hash_password(),
            "PhNumber": data.get("PhNumber"),
            "Designation": designation,
            "location": data.get("location"),
            "usertype": data.get("userType"),
            "curriculumTable": curriculum_table
        }
        
        # Insert tester
        self.insert_one(self.collections["testers"], tester)
        
        # Return response object (without password)
        return {
            "id": tester_id,
            "name": data["name"],
            "email": email,
            "PhNumber": data.get("PhNumber"),
            "Designation": designation,
            "location": data.get("location")
        }
    
    def get_testers(self) -> List[Dict]:
        """Get all testers (without passwords)"""
        projection = {
            "_id": 0, "id": 1, "name": 1, "email": 1,
            "PhNumber": 1, "Designation": 1, "location": 1
        }
        return self.find_many(self.collections["testers"], {}, projection)
    
    def update_tester(self, tester_id: str, updates: Dict) -> Dict:
        """Update tester information"""
        if not tester_id:
            raise ValidationError("ID required")
        
        # Check if tester exists
        if not self.find_one(self.collections["testers"], {"id": tester_id}):
            raise ValidationError("Tester not found")
        
        # Filter valid update fields
        valid_fields = ("name", "email", "PhNumber", "Designation", "location", "usertype")
        filtered_updates = {f: updates[f] for f in valid_fields if f in updates}
        
        # Handle curriculum update if Designation changed
        if "Designation" in filtered_updates:
            new_designation = filtered_updates["Designation"]
            subjects = new_designation if isinstance(new_designation, list) else [new_designation]
            filtered_updates["curriculumTable"] = self._build_curriculum_table(subjects)
        
        # Ensure email is lowercase
        if "email" in filtered_updates:
            filtered_updates["email"] = filtered_updates["email"].lower()
        
        if filtered_updates:
            self.update_one(
                self.collections["testers"],
                {"id": tester_id},
                {"$set": filtered_updates}
            )
        
        # Return updated tester (without password)
        return self.find_one(
            self.collections["testers"],
            {"id": tester_id},
            {"_id": 0, "password": 0}
        )
    
    def delete_tester(self, tester_id: str) -> bool:
        """Delete tester"""
        if not tester_id:
            raise ValidationError("ID required")
        
        deleted = self.delete_one(self.collections["testers"], {"id": tester_id})
        if not deleted:
            raise ValidationError("Tester not found")
        
        return True
    
    def _build_curriculum_table(self, subjects: List[str]) -> Dict:
        """Build curriculum table for subjects"""
        docs = self.find_many(
            self.collections["curriculum"],
            {"subject": {"$in": subjects}},
            {"_id": 1, "subject": 1, "Topics": 1, "SubTopics": 1, "DayOrder": 1}
        )
        
        grouped = {subj.lower(): {} for subj in subjects}
        for doc in docs:
            subj_key = doc['subject'].lower()
            sid = str(doc['_id'])
            day = doc.get('DayOrder', 'Day-Unknown')
            subtopics = [
                {"title": st, "status": False, "tag": f"{day}:{i+1}"}
                for i, st in enumerate(doc.get("SubTopics", []))
            ]
            grouped[subj_key][sid] = {
                "Topics": doc.get("Topics", []),
                "SubTopics": subtopics
            }
        
        return grouped
    
    def _hash_password(self) -> str:
        """Hash default password"""
        import os
        default_password = os.getenv("DEFAULT_TESTER_PASSWORD", "CG@Tester")
        return bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()
    
    def get_default_password(self) -> str:
        """Get default password for email"""
        import os
        return os.getenv("DEFAULT_TESTER_PASSWORD", "CG@Tester")