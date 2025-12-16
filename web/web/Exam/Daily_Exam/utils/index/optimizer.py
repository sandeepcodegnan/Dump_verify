"""Index Optimization Utilities - Database Performance (SoC)"""
from web.Exam.exam_central_db import get_db
from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
from concurrent.futures import ThreadPoolExecutor

_indexed_collections = set()

def ensure_indexes_exist(collections_to_check=None):
    """Auto-create indexes only when needed"""
    global _indexed_collections
    db = get_db()
    
    if collections_to_check:
        new_collections = set(collections_to_check) - _indexed_collections
    else:
        all_collections = db.list_collection_names()
        question_collections = [c for c in all_collections if any(c.endswith(s) for s in ['_mcq', '_code', '_query'])]
        new_collections = set(question_collections) - _indexed_collections
    
    if not new_collections:
        return
    
    def create_index_if_needed(col_name):
        try:
            collection = db[col_name]
            existing_indexes = collection.list_indexes()
            has_tags_index = any('Tags' in idx.get('key', {}) for idx in existing_indexes)
            
            if not has_tags_index:
                collection.create_index([("Tags", 1), ("Difficulty", 1)])
            _indexed_collections.add(col_name)
        except Exception:
            pass
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(create_index_if_needed, new_collections)

def create_dynamic_indexes():
    """Manual index creation for all collections"""
    global _indexed_collections
    db = get_db()
    
    curriculum_collection = db['Mentor_Curriculum_Table']
    curriculum_collection.create_index([("batch", 1), ("location", 1)])
    
    all_collections = db.list_collection_names()
    question_collections = [c for c in all_collections if any(c.endswith(s) for s in ['_mcq', '_code', '_query'])]
    
    def create_collection_index(col_name):
        try:
            collection = db[col_name]
            collection.create_index([("Tags", 1), ("Difficulty", 1)])
            _indexed_collections.add(col_name)
            print(f"✓ Indexed {col_name}")
        except Exception as e:
            print(f"✗ Failed to index {col_name}: {e}")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(create_collection_index, question_collections)
    
    print(f"Dynamic indexing completed for {len(question_collections)} collections")

if __name__ == "__main__":
    create_dynamic_indexes()