"""
Base Service Class
Common database operations following DRY principle
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId
from web.Exam.exam_central_db import db, COLLECTIONS
from web.Exam.Testing.exceptions.testing_exceptions import DatabaseError

class BaseService:
    """Base service with common database operations"""
    
    def __init__(self):
        self.db = db
        self.collections = {
            "verification": COLLECTIONS["intern_verified_questions_collection"],
            "testers": COLLECTIONS["testers_collection"],
            "dumps": COLLECTIONS["interns_dumped_collection"],
            "curriculum": COLLECTIONS["testers_curriculum_collection"]
        }
    
    def get_collection(self, collection_name: str):
        """Get MongoDB collection"""
        return self.db[collection_name]
    
    def find_one(self, collection: str, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        """Find single document"""
        try:
            return self.get_collection(collection).find_one(query, projection)
        except Exception as e:
            raise DatabaseError(f"Database query failed: {str(e)}")
    
    def find_many(self, collection: str, query: Dict, projection: Optional[Dict] = None) -> List[Dict]:
        """Find multiple documents"""
        try:
            return list(self.get_collection(collection).find(query, projection))
        except Exception as e:
            raise DatabaseError(f"Database query failed: {str(e)}")
    
    def insert_one(self, collection: str, document: Dict) -> ObjectId:
        """Insert single document"""
        try:
            result = self.get_collection(collection).insert_one(document)
            return result.inserted_id
        except Exception as e:
            raise DatabaseError(f"Database insert failed: {str(e)}")
    
    def update_one(self, collection: str, query: Dict, update: Dict, upsert: bool = False) -> bool:
        """Update single document"""
        try:
            result = self.get_collection(collection).update_one(query, update, upsert=upsert)
            return result.modified_count > 0 or (upsert and result.upserted_id)
        except Exception as e:
            raise DatabaseError(f"Database update failed: {str(e)}")
    
    def delete_one(self, collection: str, query: Dict) -> bool:
        """Delete single document"""
        try:
            result = self.get_collection(collection).delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            raise DatabaseError(f"Database delete failed: {str(e)}")
    
    def count_documents(self, collection: str, query: Dict) -> int:
        """Count documents matching query"""
        try:
            return self.get_collection(collection).count_documents(query)
        except Exception as e:
            raise DatabaseError(f"Database count failed: {str(e)}")
    
    def aggregate(self, collection: str, pipeline: List[Dict]) -> List[Dict]:
        """Execute aggregation pipeline"""
        try:
            return list(self.get_collection(collection).aggregate(pipeline))
        except Exception as e:
            raise DatabaseError(f"Database aggregation failed: {str(e)}")
    
    def get_current_utc(self) -> datetime:
        """Get current UTC datetime"""
        return datetime.utcnow()
    
    def create_index(self, collection: str, index_spec: List, unique: bool = False) -> None:
        """Create database index"""
        try:
            self.get_collection(collection).create_index(index_spec, unique=unique)
        except Exception as e:
            raise DatabaseError(f"Index creation failed: {str(e)}")