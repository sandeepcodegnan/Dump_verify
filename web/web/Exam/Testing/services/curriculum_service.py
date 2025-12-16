"""
Curriculum Service
Business logic for curriculum operations
"""
from typing import Dict, Optional
from .base_service import BaseService
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class CurriculumService(BaseService):
    """Service for curriculum operations"""
    
    def get_tester_curriculum(self, tester_id: str, subject_filter: Optional[str] = None, 
                                page: int = 1, limit: int = 10) -> Dict:
        """Get curriculum with all subjects, paginated topics within each subject"""
        if not tester_id:
            raise ValidationError("'id' query parameter is required")
        
        doc = self.find_one(
            self.collections["testers"],
            {"id": tester_id},
            {"_id": 0, "curriculumTable": 1}
        )
        
        if not doc:
            raise ValidationError("Tester not found")
        
        raw_curriculum = doc.get("curriculumTable", {})
        curriculum = {k.lower(): v for k, v in raw_curriculum.items()}
        
        if subject_filter:
            key = subject_filter.lower()
            if key not in curriculum:
                raise ValidationError(f"Subject '{subject_filter}' not found")
            curriculum = {key: curriculum[key]}
        
        # Paginate topics within each subject
        paginated_curriculum = {}
        total_topics = 0
        
        for subject, topics in curriculum.items():
            if isinstance(topics, dict):
                # Sort topics by day order
                def get_day_order(item):
                    topic_data = item[1]
                    if 'SubTopics' in topic_data and topic_data['SubTopics']:
                        tag = topic_data['SubTopics'][0].get('tag', 'Day-999:1')
                        day_part = tag.split(':')[0].replace('Day-', '').replace('DAY-', '')
                        return int(day_part) if day_part.isdigit() else 999
                    return 999
                
                topic_items = sorted(list(topics.items()), key=get_day_order)
                subject_total = len(topic_items)
                
                if subject_filter:
                    # For single subject, use normal pagination
                    total_topics = subject_total
                    start_idx = (page - 1) * limit
                    end_idx = start_idx + limit
                    paginated_topics = topic_items[start_idx:end_idx]
                    paginated_curriculum[subject] = dict(paginated_topics)
                else:
                    # For all subjects, paginate within each subject
                    total_topics += subject_total
                    start_idx = (page - 1) * limit
                    end_idx = start_idx + limit
                    paginated_topics = topic_items[start_idx:end_idx] if start_idx < subject_total else []
                    paginated_curriculum[subject] = dict(paginated_topics)
        
        total_pages = max(1, (total_topics + limit - 1) // limit)
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "id": tester_id,
            "curriculumTable": paginated_curriculum,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_topics": total_topics,
                "limit": limit,
                "has_next": has_next,
                "has_previous": has_prev
            }
        }
    
    def get_full_tester_curriculum(self, tester_id: str, subject_filter: Optional[str] = None) -> Dict:
        """Get complete curriculum for tester without pagination"""
        if not tester_id:
            raise ValidationError("'id' query parameter is required")
        
        # Fetch tester curriculum
        doc = self.find_one(
            self.collections["testers"],
            {"id": tester_id},
            {"_id": 0, "curriculumTable": 1}
        )
        
        if not doc:
            raise ValidationError("Tester not found")
        
        # Get curriculum table and normalize keys
        raw_curriculum = doc.get("curriculumTable", {})
        curriculum = {k.lower(): v for k, v in raw_curriculum.items()}
        
        # Apply subject filter if provided
        if subject_filter:
            key = subject_filter.lower()
            if key not in curriculum:
                raise ValidationError(f"Subject '{subject_filter}' not found")
            curriculum = {key: curriculum[key]}
        
        # Sort topics by day order for full curriculum too
        sorted_curriculum = {}
        for subject, topics in curriculum.items():
            if isinstance(topics, dict):
                def get_day_order(item):
                    topic_data = item[1]
                    if 'SubTopics' in topic_data and topic_data['SubTopics']:
                        tag = topic_data['SubTopics'][0].get('tag', 'Day-999:1')
                        day_part = tag.split(':')[0].replace('Day-', '').replace('DAY-', '')
                        return int(day_part) if day_part.isdigit() else 999
                    return 999
                
                sorted_topics = sorted(list(topics.items()), key=get_day_order)
                sorted_curriculum[subject] = dict(sorted_topics)
            else:
                sorted_curriculum[subject] = topics
        
        return {
            "id": tester_id,
            "curriculumTable": sorted_curriculum
        }