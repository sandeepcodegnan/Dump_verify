"""Script to fix duplicate Q_id issues in the database."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import get_collection
from utils.constants import SUBJECTS
from datetime import datetime

def find_duplicate_qids():
    """Find and report duplicate Q_ids in audit logs."""
    audit_collection = get_collection("audit_collection")
    
    print("Scanning for duplicate Q_ids...")
    
    all_qids = []
    
    # Collect all Q_ids from all activity arrays
    for intern_doc in audit_collection.find({}):
        intern_id = intern_doc.get("intern_id")
        
        activity_arrays = [
            intern_doc.get("activities", []),
            intern_doc.get("verified_modified_activities", []),
            intern_doc.get("reverified_remodified_activities", []),
            intern_doc.get("other_activities", [])
        ]
        
        for activities in activity_arrays:
            for activity in activities:
                qid = activity.get("question_id")
                action = activity.get("action")
                timestamp = activity.get("timestamp")
                
                if qid:
                    all_qids.append({
                        "qid": qid,
                        "intern_id": intern_id,
                        "action": action,
                        "timestamp": timestamp
                    })
    
    # Find duplicates
    qid_counts = {}
    for entry in all_qids:
        qid = entry["qid"]
        if qid not in qid_counts:
            qid_counts[qid] = []
        qid_counts[qid].append(entry)
    
    duplicates = {qid: entries for qid, entries in qid_counts.items() if len(entries) > 1}
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate Q_ids:")
        for qid, entries in duplicates.items():
            print(f"\nQ_id: {qid} (used {len(entries)} times)")
            for entry in entries:
                print(f"  - {entry['action']} by {entry['intern_id']} at {entry['timestamp']}")
    else:
        print("No duplicate Q_ids found!")
    
    return duplicates

def fix_mcq_collections():
    """Fix Q_id assignments in MCQ collections."""
    print("\nChecking MCQ collections for Q_id issues...")
    
    for subject_key, subject_name in SUBJECTS.items():
        try:
            collection = get_collection(f"{subject_name}_mcq")
            
            # Find questions with Q_ids
            questions_with_qids = list(collection.find({"Q_id": {"$exists": True}}))
            
            if not questions_with_qids:
                continue
            
            print(f"\n{subject_name.title()} collection:")
            print(f"  Questions with Q_ids: {len(questions_with_qids)}")
            
            # Check for duplicate Q_ids in the collection
            qid_counts = {}
            for question in questions_with_qids:
                qid = question.get("Q_id")
                if qid not in qid_counts:
                    qid_counts[qid] = []
                qid_counts[qid].append(question["_id"])
            
            duplicates_in_collection = {qid: ids for qid, ids in qid_counts.items() if len(ids) > 1}
            
            if duplicates_in_collection:
                print(f"  DUPLICATE Q_IDs found: {len(duplicates_in_collection)}")
                for qid, doc_ids in duplicates_in_collection.items():
                    print(f"    {qid}: {len(doc_ids)} documents")
                    
                    # Keep the first document, remove Q_id from others
                    for doc_id in doc_ids[1:]:
                        collection.update_one(
                            {"_id": doc_id},
                            {"$unset": {"Q_id": ""}}
                        )
                        print(f"      Removed Q_id from document {doc_id}")
            else:
                print(f"  No duplicate Q_ids in collection")
                
        except Exception as e:
            print(f"Error checking {subject_name}: {e}")

def regenerate_qids():
    """Regenerate Q_ids for questions that lost them."""
    print("\nRegenerating Q_ids for questions without them...")
    
    from services.db_service import DatabaseService
    db_service = DatabaseService()
    
    for subject_key, subject_name in SUBJECTS.items():
        try:
            collection = get_collection(f"{subject_name}_mcq")
            
            # Find questions that should have Q_ids but don't
            # (These are questions that appear in audit logs but don't have Q_ids)
            audit_collection = get_collection("audit_collection")
            
            # Get all Q_ids that should exist for this subject
            expected_qids = set()
            prefix = f"{subject_key}M"
            
            for intern_doc in audit_collection.find({}):
                activity_arrays = [
                    intern_doc.get("activities", []),
                    intern_doc.get("verified_modified_activities", []),
                    intern_doc.get("reverified_remodified_activities", []),
                    intern_doc.get("other_activities", [])
                ]
                
                for activities in activity_arrays:
                    for activity in activities:
                        qid = activity.get("question_id", "")
                        if qid.startswith(prefix):
                            expected_qids.add(qid)
            
            if not expected_qids:
                continue
            
            print(f"\n{subject_name.title()}:")
            print(f"  Expected Q_ids from audit: {len(expected_qids)}")
            
            # Check which Q_ids are missing from the collection
            existing_qids = set()
            for question in collection.find({"Q_id": {"$exists": True}}):
                existing_qids.add(question["Q_id"])
            
            missing_qids = expected_qids - existing_qids
            
            if missing_qids:
                print(f"  Missing Q_ids in collection: {len(missing_qids)}")
                print(f"  Missing: {sorted(list(missing_qids))}")
            else:
                print(f"  All expected Q_ids are present")
                
        except Exception as e:
            print(f"Error processing {subject_name}: {e}")

if __name__ == "__main__":
    print("Q_ID Duplicate Fix Tool")
    print("=" * 50)
    
    print("1. Finding duplicate Q_ids in audit logs...")
    duplicates = find_duplicate_qids()
    
    print("\n2. Checking MCQ collections...")
    fix_mcq_collections()
    
    print("\n3. Checking for missing Q_ids...")
    regenerate_qids()
    
    print("\nFix completed!")
    
    if duplicates:
        print(f"\nNote: Found {len(duplicates)} duplicate Q_ids in audit logs.")
        print("These are likely from the same question being processed multiple times.")
        print("The new Q_id generation system will prevent future duplicates.")