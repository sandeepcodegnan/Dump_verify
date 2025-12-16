from web.Exam.exam_central_db import db
from pymongo import errors
import logging

logger = logging.getLogger(__name__)

def create_collection_with_index(collection_name, index_fields, unique=False):
    """Create collection and index if they don't exist"""
    collection_names = db.list_collection_names()
    
    if collection_name not in collection_names:
        try:
            db.create_collection(collection_name)
            logger.info(f"Created MongoDB collection: {collection_name}")
        except errors.CollectionInvalid:
            logger.warning(f"Collection {collection_name} already exists")
    
    collection = db[collection_name]
    
    try:
        # Check if index already exists
        existing_indexes = collection.list_indexes()
        index_name = "_".join([f"{field}_{direction}" for field, direction in index_fields])
        
        index_exists = False
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                index_exists = True
                break
        
        if not index_exists:
            collection.create_index(index_fields, unique=unique)
            logger.info(f"Created index on {collection_name} collection")
        
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")
    
    return collection

wa_examiner_collection = create_collection_with_index("whatsapp_stats", [("date", 1), ("exam_type", 1)], unique=True)
wa_parent_collection = create_collection_with_index("parent_message_status", [("period_id", 1), ("location", 1), ("report_type", 1)])
parent_report_status_collection = create_collection_with_index("parent_report_status", [("period_id", 1), ("location", 1)])