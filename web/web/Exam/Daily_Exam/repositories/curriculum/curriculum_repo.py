"""Curriculum Repository - Data Access Layer (SoC)"""
from typing import List, Dict
from web.Exam.exam_central_db import curriculum_collection, get_db
from web.Exam.Daily_Exam.repositories.exam.exam_pipelines import (
    build_curriculum_pipeline, build_curriculum_range_pipeline, build_difficulty_breakdown_pipeline
)
from web.Exam.Daily_Exam.utils.index.optimizer import ensure_indexes_exist

class CurriculumRepo:
    def __init__(self):
        self.collection = curriculum_collection
        self.db = get_db()
    
    def get_curriculum_data(self, date: str, batch: str, location: str) -> List[Dict]:
        """Get curriculum data using complex aggregation pipeline"""
        pipeline = build_curriculum_pipeline(batch, location, date)
        return list(self.collection.aggregate(pipeline))
    
    def get_curriculum_data_range(self, start_date: str, end_date: str, batch: str, location: str) -> List[Dict]:
        """Get curriculum data for date range (Weekly-Exam)"""
        pipeline = build_curriculum_range_pipeline(batch, location, start_date, end_date)
        return list(self.collection.aggregate(pipeline))
    
    def count_by_difficulty(self, collection_name: str, tags: List[str]) -> Dict:
        """Count questions by difficulty level using pipeline with auto-indexing"""
        
        if not tags or collection_name not in self.db.list_collection_names():
            return {"easy": 0, "medium": 0, "hard": 0}
        
        # Auto-create index if needed
        ensure_indexes_exist([collection_name])
        
        collection = self.db[collection_name]
        pipeline = build_difficulty_breakdown_pipeline(tags)
        results = list(collection.aggregate(pipeline))
        
        if results and results[0]:
            breakdown = results[0]
            breakdown.pop("_id", None)
            return breakdown
        
        return {"easy": 0, "medium": 0, "hard": 0}