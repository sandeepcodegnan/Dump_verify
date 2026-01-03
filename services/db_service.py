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
        
        # Show only questions without Q_id (unverified)
        query = {"Q_id": {"$exists": False}}
        if filters:
            if filters.get('search'):
                query['Question'] = {'$regex': filters['search'], '$options': 'i'}
            if filters.get('day_tag'):
                query['Tags'] = {'$regex': f"^{filters['day_tag']}", '$options': 'i'}
        
        # Sort by Tags to maintain day order (day-1:1, day-1:2, etc.)
        questions = list(collection.find(query).sort("Tags", 1).skip(skip).limit(size))
        total = collection.count_documents(query)
        
        return {
            'questions': questions,
            'total': total,
            'page': page,
            'total_pages': (total + size - 1) // size
        }
    
    def get_day_questions(self, subject, day_number, include_verified=False):
        """Get questions for a specific day (e.g., day-1)."""
        collection = get_collection(f"{subject}_mcq")
        
        # Query for specific day tag pattern
        if include_verified:
            query = {"Tags": {"$regex": f"^day-{day_number}:", "$options": "i"}}
        else:
            query = {
                "Q_id": {"$exists": False},
                "Tags": {"$regex": f"^day-{day_number}:", "$options": "i"}
            }
        
        # Sort by tag to maintain order (day-1:1, day-1:2, etc.)
        questions = list(collection.find(query).sort("Tags", 1))
        
        return questions
    
    def get_available_days(self, subject, include_verified=False):
        """Get list of available days for a subject."""
        collection = get_collection(f"{subject}_mcq")
        
        # Get distinct day tags
        if include_verified:
            match_query = {"Tags": {"$exists": True}}
        else:
            match_query = {"Q_id": {"$exists": False}, "Tags": {"$exists": True}}
        
        pipeline = [
            {"$match": match_query},
            {"$project": {
                "day": {"$arrayElemAt": [{"$split": ["$Tags", ":"]}, 0]}
            }},
            {"$group": {"_id": "$day"}}
        ]
        
        days = [doc["_id"] for doc in collection.aggregate(pipeline) if doc["_id"]]
        
        # Sort days numerically
        def extract_day_number(day_str):
            try:
                return int(day_str.replace('day-', '').replace('Day-', ''))
            except:
                return 999
        
        return sorted(days, key=extract_day_number)
    
    def get_day_stats(self, subject, day_number):
        """Get statistics for a specific day."""
        collection = get_collection(f"{subject}_mcq")
        
        # Total questions for the day
        total_query = {"Tags": {"$regex": f"^day-{day_number}:", "$options": "i"}}
        total = collection.count_documents(total_query)
        
        # Verified questions for the day
        verified_query = {
            "Tags": {"$regex": f"^day-{day_number}:", "$options": "i"},
            "Q_id": {"$exists": True}
        }
        verified = collection.count_documents(verified_query)
        
        return {
            "total": total,
            "verified": verified,
            "remaining": total - verified
        }
    
    def reverify_question(self, question_id, intern_id, action="reverified", changes=None):
        """Re-verify already verified question without changing Q_id."""
        from bson import ObjectId
        
        # Find question in MCQ collections
        for subject_key, subject_name in SUBJECTS.items():
            source_collection = get_collection(f"{subject_name}_mcq")
            question = source_collection.find_one({"_id": ObjectId(question_id)})
            
            if question:
                # Check if already verified (has Q_id)
                existing_qid = question.get("Q_id")
                if not existing_qid:
                    return False, "Question not verified yet"
                
                # Update with changes but keep existing Q_id
                if changes:
                    source_collection.update_one(
                        {"_id": ObjectId(question_id)},
                        {"$set": changes}
                    )
                
                # Log audit with existing Q_id - ensure Q_id is preserved
                self._log_audit(existing_qid, intern_id, action, changes)
                
                return True, "Question re-verified successfully"
        
        return False, "Question not found"
    
    def generate_qid(self, subject_code, type_code):
        """Generate unique Q_id by finding the highest existing number."""
        audit_collection = get_collection("audit_collection")
        
        # Count existing unique Q_ids for this subject+type
        prefix = f"{subject_code}{type_code}"
        existing_qids = set()
        
        # Collect all unique Q_ids from all activity arrays
        for intern_doc in audit_collection.find({}):
            activity_arrays = [
                intern_doc.get("activities", []),  # Old structure
                intern_doc.get("verified_modified_activities", []),
                intern_doc.get("reverified_remodified_activities", []),
                intern_doc.get("other_activities", [])
            ]
            
            for activities in activity_arrays:
                for activity in activities:
                    qid = str(activity.get("question_id", ""))
                    if qid and qid.startswith(prefix):
                        existing_qids.add(qid)
        
        # Find the highest number used
        max_number = 0
        for qid in existing_qids:
            try:
                # Extract number from Q_id (e.g., PYM001 -> 1)
                number_part = qid[len(prefix):]
                number = int(number_part)
                max_number = max(max_number, number)
            except (ValueError, IndexError):
                continue
        
        # Generate next number
        next_number = max_number + 1
        generated_qid = f"{prefix}{next_number:03d}"
        
        # Debug log
        print(f"Generated Q_id: {generated_qid} (existing unique Q_ids: {len(existing_qids)}, max number: {max_number})")
        
        return generated_qid
    
    def verify_question(self, question_id, intern_id, action="verified", changes=None):
        """Verify MCQ question by adding Q_id to existing collection."""
        from bson import ObjectId
        
        # Find original question in MCQ collections only
        for subject_key, subject_name in SUBJECTS.items():
            source_collection = get_collection(f"{subject_name}_mcq")
            question = source_collection.find_one({"_id": ObjectId(question_id)})
            
            if question:
                # Check if already verified (has Q_id)
                existing_qid = question.get("Q_id")
                if existing_qid:
                    print(f"Question already verified with Q_id: {existing_qid}")
                    # If it's a modification action, just log the audit with existing Q_id
                    if action == "modified" and changes:
                        # Update the question with changes but keep existing Q_id
                        source_collection.update_one(
                            {"_id": ObjectId(question_id)},
                            {"$set": changes}
                        )
                        self._log_audit(existing_qid, intern_id, action, changes)
                        return True
                    return False
                
                # Generate new Q_id only if question doesn't have one
                q_id = self.generate_qid(subject_key, "M")
                
                # Update the existing document with Q_id
                update_data = {"Q_id": q_id}
                if changes:
                    update_data.update(changes)
                
                # Update the question in the same collection
                source_collection.update_one(
                    {"_id": ObjectId(question_id)},
                    {"$set": update_data}
                )
                
                # Log audit with the generated Q_id
                self._log_audit(q_id, intern_id, action, changes)
                
                return True
        return False
    
    def _log_audit(self, question_id, intern_id, action, changes=None):
        """Log audit trail with categorized activities."""
        audit_collection = get_collection("audit_collection")
        
        # Ensure question_id is not None or empty
        if not question_id:
            print(f"Warning: Empty question_id for action {action} by intern {intern_id}")
            return
        
        # Create audit entry with guaranteed question_id
        audit_entry = {
            "question_id": str(question_id),
            "action": action,
            "timestamp": datetime.now()
        }
        if changes:
            audit_entry["changes"] = changes
        
        # Determine which activity array to use
        if action in ["verified", "modified"]:
            activity_field = "verified_modified_activities"
        elif action in ["reverified", "remodified"]:
            activity_field = "reverified_remodified_activities"
        else:
            activity_field = "other_activities"
        
        # Update or create intern document with categorized activities
        audit_collection.update_one(
            {"intern_id": intern_id},
            {
                "$push": {activity_field: audit_entry},
                "$set": {"last_activity": datetime.now()}
            },
            upsert=True
        )
    
    def get_intern_stats(self, intern_id):
        """Get intern performance statistics by counting unique verified questions."""
        audit_collection = get_collection("audit_collection")
        
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        result = {"verified": 0, "modified": 0, "reverified": 0, "remodified": 0}
        
        if intern_doc:
            # Track unique question IDs for verified/modified vs reverified/remodified
            verified_modified_qids = set()
            reverified_remodified_qids = set()
            
            # Check both old and new activity structures for backward compatibility
            all_activities = []
            
            # Old structure (for backward compatibility)
            if "activities" in intern_doc:
                all_activities.extend(intern_doc["activities"])
            
            # New categorized structure
            if "verified_modified_activities" in intern_doc:
                all_activities.extend(intern_doc["verified_modified_activities"])
            if "reverified_remodified_activities" in intern_doc:
                all_activities.extend(intern_doc["reverified_remodified_activities"])
            if "other_activities" in intern_doc:
                all_activities.extend(intern_doc["other_activities"])
            
            for activity in all_activities:
                action = activity.get("action")
                qid = activity.get("question_id")
                
                if action in ["verified", "modified"] and qid:
                    verified_modified_qids.add(qid)
                elif action in ["reverified", "remodified"] and qid:
                    reverified_remodified_qids.add(qid)
            
            # Count unique questions
            result["verified"] = len([qid for qid in verified_modified_qids if not any(a.get("question_id") == qid and a.get("action") == "modified" for a in all_activities)])
            result["modified"] = len([qid for qid in verified_modified_qids if any(a.get("question_id") == qid and a.get("action") == "modified" for a in all_activities)])
            result["reverified"] = len(reverified_remodified_qids)
            result["remodified"] = 0  # Count remodified separately if needed
        
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
            collection = get_collection(f"{subject}_mcq")
            return collection.count_documents({"Q_id": {"$exists": True}})
        except:
            return 0
    
    def get_verified_today_count(self):
        """Get questions verified today from categorized audit structure."""
        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        audit_collection = get_collection("audit_collection")
        count = 0
        
        # Count from all activity arrays
        for intern_doc in audit_collection.find({}):
            activity_arrays = [
                intern_doc.get("activities", []),  # Old structure
                intern_doc.get("verified_modified_activities", []),
                intern_doc.get("reverified_remodified_activities", []),
                intern_doc.get("other_activities", [])
            ]
            
            for activities in activity_arrays:
                for activity in activities:
                    timestamp = activity.get("timestamp")
                    action = activity.get("action")
                    if timestamp and timestamp >= today and action in ["verified", "modified", "reverified", "remodified"]:
                        count += 1
        
        return count
    
    def get_all_interns(self):
        """Get all intern users."""
        users_collection = get_collection("users")
        return list(users_collection.find({"role": "intern"}))
    
    def get_top_interns(self, limit=5):
        """Get top performing interns by counting unique verified questions."""
        audit_collection = get_collection("audit_collection")
        users_collection = get_collection("users")
        
        intern_stats = {}
        
        # Count unique questions for each intern
        for intern_doc in audit_collection.find({}):
            intern_id = intern_doc.get("intern_id")
            if intern_id:
                unique_questions = set()
                activity_arrays = [
                    intern_doc.get("activities", []),  # Old structure
                    intern_doc.get("verified_modified_activities", []),
                    intern_doc.get("reverified_remodified_activities", []),
                    intern_doc.get("other_activities", [])
                ]
                
                for activities in activity_arrays:
                    for activity in activities:
                        action = activity.get("action")
                        qid = activity.get("question_id")
                        if action in ["verified", "modified"] and qid:
                            unique_questions.add(qid)
                
                if unique_questions:
                    intern_stats[intern_id] = len(unique_questions)
        
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
        total_questions = 0
        verified_count = 0
        
        # Count from each subject's MCQ collection
        for subject in SUBJECTS.values():
            try:
                collection = get_collection(f"{subject}_mcq")
                total_questions += collection.count_documents({})
                verified_count += collection.count_documents({"Q_id": {"$exists": True}})
            except:
                continue
        
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
        """Get intern stats for specific subject by counting unique verified questions."""
        audit_collection = get_collection("audit_collection")
        
        # Get subject code
        subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "XX")
        
        # Find intern document and count activities for this subject
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        result = {"verified": 0, "modified": 0, "reverified": 0, "remodified": 0}
        
        if intern_doc:
            # Track unique question IDs for this subject
            verified_modified_qids = set()
            reverified_remodified_qids = set()
            
            # Check all activity arrays
            activity_arrays = [
                intern_doc.get("activities", []),  # Old structure
                intern_doc.get("verified_modified_activities", []),
                intern_doc.get("reverified_remodified_activities", []),
                intern_doc.get("other_activities", [])
            ]
            
            all_activities = []
            for activities in activity_arrays:
                for activity in activities:
                    qid = activity.get("question_id", "")
                    action = activity.get("action")
                    # Check if question ID starts with subject code + M (for MCQ)
                    if qid.startswith(f"{subject_code}M"):
                        all_activities.append(activity)
                        if action in ["verified", "modified"]:
                            verified_modified_qids.add(qid)
                        elif action in ["reverified", "remodified"]:
                            reverified_remodified_qids.add(qid)
            
            # Count unique questions for this subject
            result["verified"] = len([qid for qid in verified_modified_qids if not any(a.get("question_id") == qid and a.get("action") == "modified" for a in all_activities)])
            result["modified"] = len([qid for qid in verified_modified_qids if any(a.get("question_id") == qid and a.get("action") == "modified" for a in all_activities)])
            result["reverified"] = len(reverified_remodified_qids)
            result["remodified"] = 0  # Count remodified separately if needed
        
        return result
    
    def get_audit_logs(self, date_from=None, action=None, intern=None, limit=50):
        """Get audit logs with filters from categorized structure."""
        audit_collection = get_collection("audit_collection")
        
        # Get all intern documents
        intern_docs = audit_collection.find({})
        
        all_activities = []
        for intern_doc in intern_docs:
            intern_id = intern_doc.get("intern_id")
            
            # Collect from all activity arrays (old and new structure)
            activity_arrays = [
                intern_doc.get("activities", []),  # Old structure
                intern_doc.get("verified_modified_activities", []),
                intern_doc.get("reverified_remodified_activities", []),
                intern_doc.get("other_activities", [])
            ]
            
            for activities in activity_arrays:
                for activity in activities:
                    # Add intern_id to each activity for filtering
                    activity_with_intern = activity.copy()
                    activity_with_intern["intern_id"] = intern_id
                    
                    # Apply filters
                    if date_from and activity.get("timestamp"):
                        if activity["timestamp"] < datetime.combine(date_from, datetime.min.time()):
                            continue
                    
                    if action and activity.get("action") != action:
                        continue
                    
                    if intern and intern_id != intern:
                        continue
                    
                    all_activities.append(activity_with_intern)
        
        # Sort by timestamp descending and limit
        all_activities.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        
        return all_activities[:limit]
    
    def get_first_unverified_question_index(self, subject):
        """Find the index of first unverified question."""
        collection = get_collection(f"{subject}_mcq")
        
        # Count verified questions (those with Q_id)
        verified_count = collection.count_documents({"Q_id": {"$exists": True}})
        return verified_count + 1  # Start from next unverified question
    
    def is_question_verified(self, question_id, subject):
        """Check if a question is already verified by checking if it has Q_id."""
        from bson import ObjectId
        
        # Get the question from source collection
        source_collection = get_collection(f"{subject}_mcq")
        question = source_collection.find_one({"_id": ObjectId(question_id)})
        
        if not question:
            return False
        
        # Check if question has Q_id (verified)
        return question.get("Q_id") is not None
    
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
        subjects = {}
        
        # Check each subject's MCQ collection for verified questions (those with Q_id)
        for subject in SUBJECTS.values():
            try:
                collection = get_collection(f"{subject}_mcq")
                count = collection.count_documents({"Q_id": {"$exists": True}})
                if count > 0:
                    subjects[subject] = count
            except:
                continue
        
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
    


    def get_last_activity(self, intern_id, subject):
        """Get last activity timestamp for subject by sorting all activities by timestamp."""
        audit_collection = get_collection("audit_collection")
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        
        if not intern_doc:
            return None
        
        # Get subject code
        subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "XX")
        
        activity_arrays = [
            intern_doc.get("verified_modified_activities", []),
            intern_doc.get("reverified_remodified_activities", [])
        ]
        
        # Collect all activities for this subject
        subject_activities = []
        
        for activities in activity_arrays:
            for activity in activities:
                qid = activity.get("question_id", "")
                timestamp = activity.get("timestamp")
                
                # Check if it's for this subject
                if qid.startswith(f"{subject_code}M") and timestamp:
                    subject_activities.append(activity)
        
        # Sort by timestamp and get last
        if not subject_activities:
            return None
        
        subject_activities.sort(key=lambda x: x.get("timestamp"))
        latest_activity = subject_activities[-1]
        latest_utc_timestamp = latest_activity.get("timestamp")
        
        if latest_utc_timestamp:
            from datetime import timezone, timedelta
            
            # IST timezone (UTC + 5:30)
            ist_timezone = timezone(timedelta(hours=5, minutes=30))
            
            # Convert UTC DB timestamp to IST
            latest_utc_timestamp = latest_utc_timestamp.replace(tzinfo=timezone.utc)
            latest_ist_timestamp = latest_utc_timestamp.astimezone(ist_timezone)
            
            # Get current IST time
            current_ist_time = datetime.now(ist_timezone)
            
            # Calculate difference in IST
            delta = current_ist_time - latest_ist_timestamp
            
            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            else:
                return f"{delta.seconds // 60}m ago"
        
        return None
    
    def get_daily_average(self, intern_id, subject):
        """Calculate daily average questions for subject."""
        audit_collection = get_collection("audit_collection")
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        
        if not intern_doc:
            return 0.0
        
        # Get subject code
        subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "XX")
        
        # Get first activity date for this subject
        first_date = None
        activity_arrays = [
            intern_doc.get("activities", []),
            intern_doc.get("verified_modified_activities", []),
            intern_doc.get("reverified_remodified_activities", []),
            intern_doc.get("other_activities", [])
        ]
        
        subject_activities = []
        for activities in activity_arrays:
            for activity in activities:
                qid = activity.get("question_id", "")
                if qid.startswith(f"{subject_code}M") and activity.get("action") in ["verified", "modified"]:
                    subject_activities.append(activity)
                    timestamp = activity.get("timestamp")
                    if timestamp and (not first_date or timestamp < first_date):
                        first_date = timestamp
        
        if not first_date or not subject_activities:
            return 0.0
        
        # Calculate days since first activity
        days_active = max(1, (datetime.now() - first_date).days + 1)
        unique_questions = len(set(a.get("question_id") for a in subject_activities))
        
        return unique_questions / days_active
    
    def get_questions_today(self, intern_id, subject):
        """Get questions completed today for subject or all subjects if subject is None."""
        audit_collection = get_collection("audit_collection")
        intern_doc = audit_collection.find_one({"intern_id": intern_id})
        
        if not intern_doc:
            return 0
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_questions = set()
        
        activity_arrays = [
            intern_doc.get("activities", []),
            intern_doc.get("verified_modified_activities", []),
            intern_doc.get("reverified_remodified_activities", []),
            intern_doc.get("other_activities", [])
        ]
        
        for activities in activity_arrays:
            for activity in activities:
                qid = activity.get("question_id", "")
                timestamp = activity.get("timestamp")
                action = activity.get("action")
                
                # If subject is None, count all subjects; otherwise filter by subject
                if subject is None:
                    # Count all questions for today
                    if (timestamp and timestamp >= today and 
                        action in ["verified", "modified"] and qid):
                        today_questions.add(qid)
                else:
                    # Get subject code and filter
                    subject_code = next((k for k, v in SUBJECTS.items() if v == subject), "XX")
                    if (qid.startswith(f"{subject_code}M") and 
                        timestamp and timestamp >= today and 
                        action in ["verified", "modified"]):
                        today_questions.add(qid)
        
        return len(today_questions)
    
    