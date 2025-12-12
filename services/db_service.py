"""Database service for optimized MongoDB operations."""
import streamlit as st
import os
from datetime import datetime
from config.database import get_collection
from utils.constants import SUBJECTS, TYPES
from pymongo import InsertOne

class DatabaseService:
    def __init__(self):
        pass
    
    def get_paginated_questions(self, subject, page=1, size=50, filters=None, question_type="mcq"):
        """Get paginated questions with caching (MCQ only)."""
        collection = get_collection(f"{subject}_mcq")
        skip = (page - 1) * size
        
        # Show questions not yet processed (check nested audit_collection)
        audit_collection = get_collection("audit_collection")
        subject_code = list(SUBJECTS.keys())[list(SUBJECTS.values()).index(subject)]
        
        # Get processed question IDs from nested structure
        processed_qids = []
        for intern_doc in audit_collection.find({}, {"activities": 1}):
            for activity in intern_doc.get("activities", []):
                qid = activity.get("question_id", "")
                if qid.startswith(f"{subject_code}M") and activity.get("action") in ["verified", "modified"]:
                    processed_qids.append(qid)
        
        query = {"Q_id": {"$nin": processed_qids}} if processed_qids else {}
        if filters:
            if filters.get('search'):
                query['Question'] = {'$regex': filters['search'], '$options': 'i'}
        
        questions = list(collection.find(query).skip(skip).limit(size))
        total = collection.count_documents(query)
        
        # Debug: Check total vs all documents
        all_docs = collection.count_documents({})
        print(f"DEBUG: Subject {subject} - Total docs: {all_docs}, Unverified: {total}")
        
        return {
            'questions': questions,
            'total': total,
            'page': page,
            'total_pages': (total + size - 1) // size
        }
    
    def generate_qid(self, subject_code, type_code):
        """Generate unique Q_id from audit_collection count."""
        audit_collection = get_collection("audit_collection")
        
        # Count existing Q_ids for this subject+type from audit_collection
        prefix = f"{subject_code}{type_code}"
        
        # Count all activities with Q_ids starting with this prefix
        count = 0
        for intern_doc in audit_collection.find({}, {"activities": 1}):
            for activity in intern_doc.get("activities", []):
                qid = activity.get("question_id", "")
                if qid.startswith(prefix):
                    count += 1
        
        # Generate next number
        next_number = count + 1
        return f"{prefix}{next_number:03d}"
    
    def verify_question(self, question_id, intern_id, action="verified", changes=None):
        """Verify and migrate MCQ question to verified collection."""
        from bson import ObjectId
        
        # Find original question in MCQ collections only
        for subject_key, subject_name in SUBJECTS.items():
            source_collection = get_collection(f"{subject_name}_mcq")
            question = source_collection.find_one({"_id": ObjectId(question_id)})
            
            if question:
                # Generate Q_id (e.g., PYM001)
                q_id = self.generate_qid(subject_key, "M")
                
                # Update question data
                question["Q_id"] = q_id
                
                if changes:
                    question.update(changes)
                
                # Move to verified collection (e.g., py_mcq_verified)
                verified_collection_name = f"{subject_key.lower()}_mcq_verified"
                verified_collection = get_collection(verified_collection_name)
                
                # Check if question already exists in verified collection
                existing = verified_collection.find_one({"questionId": question.get("questionId")})
                if existing:
                    print(f"Question already verified: {question.get('questionId')}")
                    return False
                
                # Remove _id to avoid duplicate key error, let MongoDB generate new one
                if "_id" in question:
                    del question["_id"]
                
                # Insert to verified collection (copy only, keep source as reference)
                verified_collection.insert_one(question)
                
                # Log audit
                self._log_audit(q_id, intern_id, action, changes)
                

                
                return True
        return False
    
    def _log_audit(self, question_id, intern_id, action, changes=None):
        """Log audit trail with optimized nested structure."""
        audit_collection = get_collection("audit_collection")
        
        # Create audit entry
        audit_entry = {
            "question_id": question_id,
            "action": action,
            "timestamp": datetime.now()
        }
        if changes:
            audit_entry["changes"] = changes
        
        # Update or create intern document with nested activities
        audit_collection.update_one(
            {"intern_id": intern_id},
            {
                "$push": {"activities": audit_entry},
                "$set": {"last_activity": datetime.now()}
            },
            upsert=True
        )
    
    def get_intern_stats(self, intern_id):
        """Get intern performance statistics from nested structure."""
        audit_collection = get_collection("audit_collection")
        
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        result = {"verified": 0, "modified": 0}
        
        if intern_doc and "activities" in intern_doc:
            for activity in intern_doc["activities"]:
                action = activity.get("action")
                if action in result:
                    result[action] += 1
        
        return result
    
    def get_subject_question_count(self, subject):
        """Get total questions for a subject."""
        try:
            collection = get_collection(f"{subject}_mcq")
            return collection.count_documents({})
        except:
            return 0
    
    def get_verified_count(self, subject):
        """Get verified questions count for a subject."""
        try:
            subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "xx")
            collection = get_collection(f"{subject_code.lower()}_mcq_verified")
            return collection.count_documents({})
        except:
            return 0
    
    def get_verified_today_count(self):
        """Get questions verified today from nested audit structure."""
        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        audit_collection = get_collection("audit_collection")
        count = 0
        
        # Count from nested activities
        for intern_doc in audit_collection.find({}, {"activities": 1}):
            for activity in intern_doc.get("activities", []):
                timestamp = activity.get("timestamp")
                action = activity.get("action")
                if timestamp and timestamp >= today and action in ["verified", "modified"]:
                    count += 1
        
        return count
    
    def get_all_interns(self):
        """Get all intern users."""
        users_collection = get_collection("users")
        return list(users_collection.find({"role": "intern"}))
    
    def get_top_interns(self, limit=5):
        """Get top performing interns from nested audit structure."""
        audit_collection = get_collection("audit_collection")
        users_collection = get_collection("users")
        
        intern_stats = {}
        
        # Count from nested activities
        for intern_doc in audit_collection.find({}, {"intern_id": 1, "activities": 1}):
            intern_id = intern_doc.get("intern_id")
            if intern_id:
                count = len([a for a in intern_doc.get("activities", []) 
                           if a.get("action") in ["verified", "modified"]])
                if count > 0:
                    intern_stats[intern_id] = count
        
        # Sort and limit
        sorted_interns = sorted(intern_stats.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        results = []
        for intern_id, verified_count in sorted_interns:
            user = users_collection.find_one({"user_id": intern_id})
            results.append({
                "_id": intern_id,
                "verified": verified_count,
                "name": user["name"] if user else intern_id
            })
        
        return results
    
    def get_overall_completion_rate(self):
        """Calculate overall completion rate across all subjects."""
        # Get total questions across all subjects
        total_questions = 0
        for subject in SUBJECTS.values():
            total_questions += self.get_subject_question_count(subject)
        
        # Get total verified questions from audit
        audit_collection = get_collection("audit_collection")
        verified_count = 0
        
        for intern_doc in audit_collection.find({}, {"activities": 1}):
            for activity in intern_doc.get("activities", []):
                if activity.get("action") in ["verified", "modified"]:
                    verified_count += 1
        
        return (verified_count / total_questions * 100) if total_questions > 0 else 0.0
    
    def allocate_questions(self, intern_id, subjects, quotas):
        """Allocate questions to intern by updating user document."""
        users_collection = get_collection("users")
        
        # Get current allocated subjects
        user = users_collection.find_one({"user_id": intern_id})
        if not user:
            return False
        
        current_subjects = user.get("allocated_subjects", [])
        
        # Add new subjects to existing ones
        updated_subjects = list(set(current_subjects + subjects))
        
        # Update user document
        result = users_collection.update_one(
            {"user_id": intern_id},
            {
                "$set": {
                    "allocated_subjects": updated_subjects,
                    "last_allocation": datetime.now()
                }
            }
        )
        
        return result.modified_count > 0
    
    def get_current_allocations(self):
        """Get current question allocations from user documents."""
        users_collection = get_collection("users")
        
        # Get all interns with allocated subjects
        interns = list(users_collection.find({
            "role": "intern",
            "allocated_subjects": {"$exists": True, "$ne": []}
        }))
        
        allocations = []
        for intern in interns:
            subjects = intern.get("allocated_subjects", [])
            if subjects:
                # Calculate total questions
                total_quota = 0
                for subject in subjects:
                    total_quota += self.get_subject_question_count(subject)
                
                # Get completed count
                stats = self.get_intern_stats(intern["user_id"])
                completed = stats["verified"] + stats["modified"]
                
                allocations.append({
                    "intern_id": intern["user_id"],
                    "intern_name": intern["name"],
                    "subjects": subjects,
                    "total_quota": total_quota,
                    "completed": completed
                })
        
        return allocations
    
    def get_intern_assignments(self, intern_id):
        """Get intern's current assignments from user document."""
        users_collection = get_collection("users")
        user = users_collection.find_one({"user_id": intern_id})
        
        if user and user.get("allocated_subjects"):
            subjects = user["allocated_subjects"]
            quotas = {}
            for subject in subjects:
                quotas[subject] = self.get_subject_question_count(subject)
            
            return {
                "subjects": subjects,
                "quotas": quotas
            }
        
        return None
    
    def get_intern_subject_stats(self, intern_id, subject):
        """Get intern stats for specific subject from nested audit structure."""
        audit_collection = get_collection("audit_collection")
        
        # Get subject code
        subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "XX")
        
        # Find intern document and count activities for this subject
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        result = {"verified": 0, "modified": 0}
        
        if intern_doc and "activities" in intern_doc:
            for activity in intern_doc["activities"]:
                qid = activity.get("question_id", "")
                action = activity.get("action")
                # Check if question ID starts with subject code + M (for MCQ)
                if qid.startswith(f"{subject_code}M") and action in result:
                    result[action] += 1
        
        return result
    
    def get_audit_logs(self, date_from=None, action=None, intern=None, limit=50):
        """Get audit logs with filters."""
        audit_collection = get_collection("audit_collection")
        
        query = {}
        if date_from:
            query["timestamp"] = {"$gte": datetime.combine(date_from, datetime.min.time())}
        if action:
            query["action"] = action
        if intern:
            query["intern_id"] = intern
        
        return list(audit_collection.find(query).sort("timestamp", -1).limit(limit))
    
    def get_first_unverified_question_index(self, subject):
        """Find the index of first unverified question."""
        collection = get_collection(f"{subject}_mcq")
        audit_collection = get_collection("audit_collection")
        subject_code = list(SUBJECTS.keys())[list(SUBJECTS.values()).index(subject)]
        
        # Get processed question IDs from nested structure
        processed_qids = []
        for intern_doc in audit_collection.find({}, {"activities": 1}):
            for activity in intern_doc.get("activities", []):
                qid = activity.get("question_id", "")
                if qid.startswith(f"{subject_code}M") and activity.get("action") in ["verified", "modified"]:
                    processed_qids.append(qid)
        
        # Count verified questions to find first unverified index
        verified_count = len(processed_qids)
        return verified_count + 1  # Start from next unverified question
    
    def is_question_verified(self, question_id, subject):
        """Check if a question is already verified by checking if its questionId exists in verified collection."""
        from bson import ObjectId
        
        # Get the question from source collection to get its questionId
        source_collection = get_collection(f"{subject}_mcq")
        question = source_collection.find_one({"_id": ObjectId(question_id)})
        
        if not question or not question.get("questionId"):
            return False
        
        # Check if questionId exists in verified collection
        subject_code = list(SUBJECTS.keys())[list(SUBJECTS.values()).index(subject)]
        verified_collection = get_collection(f"{subject_code.lower()}_mcq_verified")
        
        existing = verified_collection.find_one({"questionId": question["questionId"]})
        return existing is not None
    
    def get_question_batch(self, subject, batch_size=10):
        """Get batch of questions for bulk verification."""
        collection = get_collection(f"{subject}_mcq")
        return list(collection.find({}).limit(batch_size))
    
    def bulk_verify_clean_questions(self, subject, question_type, batch_size):
        """Bulk verify questions that meet quality criteria."""
        # Simulate bulk verification
        return {"verified": batch_size, "skipped": 0}
    
    def generate_verification_report(self, subject):
        """Generate verification report for subject."""
        total = self.get_subject_question_count(subject)
        verified = self.get_verified_count(subject)
        
        return {
            "subject": subject,
            "total_questions": total,
            "verified_questions": verified,
            "completion_rate": round((verified / total * 100) if total > 0 else 0, 2),
            "remaining": total - verified
        }
    
    def get_available_subjects(self):
        """Get all available subjects with question counts from database."""
        db = get_collection("users").database  # Get database reference
        collections = db.list_collection_names()
        
        subjects = {}
        for collection_name in collections:
            if collection_name.endswith('_mcq'):
                subject = collection_name.replace('_mcq', '')
                count = db[collection_name].count_documents({})
                if count > 0:
                    subjects[subject] = count
        
        return subjects
    
    def get_verified_subjects(self):
        """Get all verified subjects with counts from database."""
        db = get_collection("users").database  # Get database reference
        collections = db.list_collection_names()
        
        subjects = {}
        for collection_name in collections:
            if collection_name.endswith('_verified'):
                # Extract subject from collection name (e.g., py_mcq_verified -> python)
                parts = collection_name.replace('_verified', '').split('_')
                if len(parts) >= 2:
                    subject_code = parts[0].upper()
                    # Find full subject name
                    subject = next((v for k, v in SUBJECTS.items() if k == subject_code), parts[0])
                    count = db[collection_name].count_documents({})
                    if count > 0:
                        subjects[subject] = count
        
        return subjects
    
    def get_intern_allocated_subjects(self, intern_id):
        """Get subjects already allocated to an intern from user document."""
        users_collection = get_collection("users")
        user = users_collection.find_one({"user_id": intern_id})
        
        if user:
            return user.get("allocated_subjects", [])
        return []
    
    def get_unallocated_subjects(self):
        """Get subjects that are not allocated to any intern."""
        available_subjects = self.get_available_subjects()
        users_collection = get_collection("users")
        
        # Get all allocated subjects from all interns
        allocated_subjects = set()
        interns = users_collection.find({"role": "intern", "allocated_subjects": {"$exists": True}})
        
        for intern in interns:
            subjects = intern.get("allocated_subjects", [])
            allocated_subjects.update(subjects)
        
        # Return only unallocated subjects
        unallocated = {k: v for k, v in available_subjects.items() if k not in allocated_subjects}
        return unallocated
    
    def create_intern_user(self, name, email, allocated_subjects):
        """Create new intern user with allocated subjects."""
        users_collection = get_collection("users")
        
        # Generate username from email prefix
        username = email.split('@')[0]
        
        # Generate unique user_id by finding the highest existing number
        existing_interns = list(users_collection.find(
            {"role": "intern", "user_id": {"$regex": "^INT"}},
            {"user_id": 1}
        ))
        
        max_num = 0
        for intern in existing_interns:
            try:
                num = int(intern["user_id"][3:])  # Extract number after "INT"
                max_num = max(max_num, num)
            except:
                continue
        
        user_id = f"INT{max_num + 1:03d}"
        
        # Default password from environment
        default_password = os.getenv("DEFAULT_INTERN_PASSWORD", "CG@intern")
        
        # Create user document
        user_data = {
            "user_id": user_id,
            "username": username,
            "password": default_password,
            "name": name,
            "role": "intern",
            "email": email,
            "allocated_subjects": allocated_subjects,
            "created_at": datetime.now(),
            "status": "active"
        }
        
        # Check if username already exists
        if users_collection.find_one({"username": username}):
            return None, "Username already exists"
        
        # Insert user
        result = users_collection.insert_one(user_data)
        
        if result.inserted_id:
            return {
                "user_id": user_id,
                "username": username,
                "password": default_password,
                "email": email,
                "allocated_subjects": allocated_subjects
            }, None
        
        return None, "Failed to create user"