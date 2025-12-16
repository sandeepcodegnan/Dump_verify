"""Question Domain Pipelines - Question DB Queries (SoC)"""
from typing import List, Dict

# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION FETCH PIPELINES
# ═══════════════════════════════════════════════════════════════════════════════

def build_question_fetch_pipeline(tags: List[str], difficulty: str, count: int, include_metadata: bool = False) -> List[Dict]:
    """Build aggregation pipeline for fetching random questions"""
    search_tags = [t.lower() for t in tags]
    diff_val = difficulty.capitalize()
    
    pipeline = [
        {"$match": {"Tags": {"$in": search_tags}, "Difficulty": diff_val}},
        {"$sample": {"size": count}},
        {"$addFields": {"questionId": {"$toString": "$_id"}}},
        {"$unset": "_id"}  # Remove _id to ensure consistent format
    ]
    
    if include_metadata:
        pipeline.append({
            "$addFields": {
                "metadata": {
                    "fetchedAt": "$$NOW",
                    "difficulty": "$Difficulty",
                    "tags": "$Tags"
                }
            }
        })
    
    return pipeline