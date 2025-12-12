"""Migration script to reorganize audit activities into categorized arrays."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import get_collection
from datetime import datetime

def migrate_audit_structure():
    """Migrate existing audit structure to categorized activities."""
    audit_collection = get_collection("audit_collection")
    
    print("Starting audit structure migration...")
    
    # Get all intern documents
    intern_docs = list(audit_collection.find({}))
    
    migrated_count = 0
    
    for intern_doc in intern_docs:
        intern_id = intern_doc.get("intern_id")
        activities = intern_doc.get("activities", [])
        
        if not activities:
            continue
        
        # Categorize activities
        verified_modified = []
        reverified_remodified = []
        other_activities = []
        
        for activity in activities:
            action = activity.get("action")
            
            if action in ["verified", "modified"]:
                verified_modified.append(activity)
            elif action in ["reverified", "remodified"]:
                reverified_remodified.append(activity)
            else:
                other_activities.append(activity)
        
        # Update document with categorized activities
        update_data = {}
        
        if verified_modified:
            update_data["verified_modified_activities"] = verified_modified
        
        if reverified_remodified:
            update_data["reverified_remodified_activities"] = reverified_remodified
        
        if other_activities:
            update_data["other_activities"] = other_activities
        
        # Add migration timestamp
        update_data["migration_timestamp"] = datetime.now()
        
        if update_data:
            audit_collection.update_one(
                {"intern_id": intern_id},
                {"$set": update_data}
            )
            
            migrated_count += 1
            print(f"Migrated intern {intern_id}: {len(verified_modified)} verified/modified, {len(reverified_remodified)} reverified/remodified")
    
    print(f"\nMigration completed! Migrated {migrated_count} intern documents.")
    print("Note: Original 'activities' array is preserved for backward compatibility.")

def verify_migration():
    """Verify the migration was successful."""
    audit_collection = get_collection("audit_collection")
    
    print("\nVerifying migration...")
    
    intern_docs = list(audit_collection.find({}))
    
    for intern_doc in intern_docs:
        intern_id = intern_doc.get("intern_id")
        
        # Count activities in old structure
        old_activities = len(intern_doc.get("activities", []))
        
        # Count activities in new structure
        verified_modified = len(intern_doc.get("verified_modified_activities", []))
        reverified_remodified = len(intern_doc.get("reverified_remodified_activities", []))
        other_activities = len(intern_doc.get("other_activities", []))
        
        new_total = verified_modified + reverified_remodified + other_activities
        
        print(f"Intern {intern_id}:")
        print(f"  Old structure: {old_activities} activities")
        print(f"  New structure: {new_total} activities ({verified_modified} v/m, {reverified_remodified} rv/rm, {other_activities} other)")
        
        if old_activities != new_total:
            print(f"  WARNING: Activity count mismatch!")
        else:
            print(f"  OK: Activity counts match")

if __name__ == "__main__":
    print("Audit Structure Migration Tool")
    print("=" * 50)
    
    choice = input("Choose action:\n1. Migrate structure\n2. Verify migration\n3. Both\nEnter choice (1-3): ")
    
    if choice in ["1", "3"]:
        migrate_audit_structure()
    
    if choice in ["2", "3"]:
        verify_migration()
    
    print("\nMigration tool completed!")