from datetime import datetime, timedelta
from web.Exam.exam_central_db import db, student_collection as students_coll
import json
from functools import lru_cache
import threading

# Ultra-fast metrics collection with memory caching
metrics_coll = db.student_leaderboard_metrics

# In-memory cache for ultra-fast access
_cache = {}
_cache_lock = threading.RLock()
_cache_ttl = 30  # 30 seconds cache for production

class UltraFastLeaderboard:
    
    @staticmethod
    def _get_cache_key(mode, batch_no, location, page, limit):
        """Generate cache key for request"""
        return f"{mode}:{batch_no}:{location}:{page}:{limit}"
    
    @staticmethod
    def _is_cache_valid(timestamp):
        """Check if cache entry is still valid"""
        return datetime.utcnow() - timestamp < timedelta(seconds=_cache_ttl)
    
    @staticmethod
    def _get_from_cache(cache_key):
        """Get data from memory cache"""
        with _cache_lock:
            if cache_key in _cache:
                data, timestamp = _cache[cache_key]
                if UltraFastLeaderboard._is_cache_valid(timestamp):
                    return data
                else:
                    del _cache[cache_key]
        return None
    
    @staticmethod
    def _set_cache(cache_key, data):
        """Set data in memory cache"""
        with _cache_lock:
            _cache[cache_key] = (data, datetime.utcnow())
            # Keep cache size manageable
            if len(_cache) > 100:
                # Remove oldest entries
                oldest_keys = sorted(_cache.keys(), key=lambda k: _cache[k][1])[:20]
                for key in oldest_keys:
                    del _cache[key]
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def _build_filter_query(mode, batch_no, location):
        """Cached filter query builder"""
        if mode == 'batch':
            return json.dumps({"batchNo": batch_no, "location": location}), f"Batch {batch_no} - {location}"
        elif mode == 'course':
            course_code = batch_no.split('-')[0]
            return json.dumps({"batchNo": {"$regex": f"^{course_code}-"}, "location": location}), f"Course {course_code} - {location}"
        elif mode == 'global':
            return json.dumps({}), "Global (All Locations)"
        else:
            raise ValueError("Invalid mode")
    
    @staticmethod
    def _format_time_fast(seconds):
        """Ultra-fast time formatting"""
        if seconds < 60:
            return f"{int(seconds)}s"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    
    @staticmethod
    def get_leaderboard_ultra_fast(mode, batch_no=None, location=None, page=1, limit=10, student_id=None):
        """Ultra-fast leaderboard with aggressive caching and optimizations"""
        
        # Input validation (fast fail)
        if mode not in ['batch', 'course', 'global']:
            return {"error": "Invalid mode"}, 400
        if mode in ['batch', 'course'] and (not batch_no or not location):
            return {"error": f"batchNo and location required for {mode} mode"}, 400
        
        # Check cache first (skip cache if student_id provided for fresh data)
        cache_key = UltraFastLeaderboard._get_cache_key(mode, batch_no or '', location or '', page, limit)
        cached_result = None if student_id else UltraFastLeaderboard._get_from_cache(cache_key)
        if cached_result:
            return cached_result, 200
        
        # Build query
        filter_json, scope = UltraFastLeaderboard._build_filter_query(mode, batch_no or '', location or '')
        filter_query = json.loads(filter_json)
        
        skip = (page - 1) * limit
        
        # Ultra-optimized aggregation pipeline with proper ranking sort
        pipeline = [
            {"$match": filter_query},
            {"$sort": {
                "total_score": -1,           # Primary: Higher score = better rank
                "avg_execution_time": 1,     # Tiebreaker 1: Lower execution time = better rank
                "total_time_spent": 1,       # Tiebreaker 2: Lower time spent = better rank  
                "max_memory_used_mb": 1,     # Tiebreaker 3: Lower memory = better rank
                "questions_solved": -1       # Tiebreaker 4: More questions = better rank
            }},
            {"$skip": skip},
            {"$limit": limit},
            {"$project": {  # Only get what we need
                "name": 1,
                "batchNo": 1, 
                "location": 1,
                "studentId": 1,
                "student_id": 1,
                "total_score": 1,
                "questions_solved": 1,
                "difficulty_breakdown": 1,
                "total_time_spent": 1,
                "avg_execution_time": 1,
                "max_memory_used_mb": 1,
                "difficulty_score": 1
            }}
        ]
        
        # Execute query
        leaderboard_data = list(metrics_coll.aggregate(pipeline))
        
        # Fast count (estimate for better performance)
        total_count = metrics_coll.estimated_document_count() if not filter_query else metrics_coll.count_documents(filter_query)
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        # Build response with optimized ranking (use position as rank for performance)
        rank_list = []
        for pos, item in enumerate(leaderboard_data, start=skip + 1):
            # Use position as rank for better performance (since data is already sorted correctly)
            actual_rank = pos
            
            rank_list.append({
                "position": pos,
                "rank": actual_rank,
                "name": item.get("name", ""),
                "batchNo": item.get("batchNo", ""),
                "location": item.get("location", ""),
                "total_score": item.get("total_score", 0),
                "questions_solved": item.get("questions_solved", 0),
                "difficulty_breakdown": item.get("difficulty_breakdown", {"easy": 0, "medium": 0, "hard": 0}),
                "total_time_spent": UltraFastLeaderboard._format_time_fast(item.get("total_time_spent", 0)),
                "avg_execution_time": f"{round(item.get('avg_execution_time', 0), 1)}ms",
                "max_memory_used": f"{round(item.get('max_memory_used_mb', 0), 2):.2f}MB",
                "difficulty_score": item.get("difficulty_score", 0),
                "img": f"/api/v1/pic?student_id={item.get('studentId', '')}",
                "student_id": item.get("student_id", "")
            })
        
        result = {
            "success": True,
            "mode": mode,
            "scope": scope,
            "student_data": None,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "per_page": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "leaderboard": rank_list
        }
        
        # Cache the result
        UltraFastLeaderboard._set_cache(cache_key, result)
        
        # Handle student lookup - only add if student is on current page
        if student_id:
            result = UltraFastLeaderboard._add_student_to_result(
                result, student_id, filter_query, limit, page
            )
        
        return result, 200
    
    @staticmethod
    def _add_student_to_result(result, student_id, filter_query, limit, current_page):
        """Add student rank info to result"""
        # Fast student lookup
        student_data = metrics_coll.find_one({"student_id": student_id, **filter_query})
        if student_data:
            # Fast rank calculation using aggregation pipeline
            rank_pipeline = [
                {"$match": filter_query},
                {"$sort": {
                    "total_score": -1,           # Primary: Higher score = better rank
                    "avg_execution_time": 1,     # Tiebreaker 1: Lower execution time = better rank
                    "total_time_spent": 1,       # Tiebreaker 2: Lower time spent = better rank
                    "max_memory_used_mb": 1,     # Tiebreaker 3: Lower memory = better rank
                    "questions_solved": -1       # Tiebreaker 4: More questions = better rank
                }},
                {"$group": {"_id": None, "students": {"$push": "$student_id"}}}
            ]
            
            rank_result = list(metrics_coll.aggregate(rank_pipeline))
            if rank_result and "students" in rank_result[0]:
                student_ids = rank_result[0]["students"]
                if student_id in student_ids:
                    rank = student_ids.index(student_id) + 1
                    actual_position = rank
                else:
                    # Student not found in filtered results - shouldn't happen
                    print(f"Warning: Student {student_id} not found in ranking results")
                    return result  # Return without student_rank
            else:
                # No ranking data available - shouldn't happen
                print(f"Warning: No ranking data available for filter {filter_query}")
                return result  # Return without student_rank
            student_page = ((actual_position - 1) // limit) + 1
            is_on_current_page = student_page == current_page
            
            # Send student_data on current page or pages before their actual page
            if is_on_current_page or current_page <= student_page:
                result["student_data"] = {
                    "student_id": student_id,
                    "rank": rank,
                    "page": student_page,
                    "is_on_current_page": is_on_current_page,
                    "name": student_data.get("name", ""),
                    "batchNo": student_data.get("batchNo", ""),
                    "location": student_data.get("location", ""),
                    "total_score": student_data.get("total_score", 0),
                    "questions_solved": student_data.get("questions_solved", 0),
                    "difficulty_breakdown": student_data.get("difficulty_breakdown", {"easy": 0, "medium": 0, "hard": 0}),
                    "total_time_spent": UltraFastLeaderboard._format_time_fast(student_data.get("total_time_spent", 0)),
                    "avg_execution_time": f"{round(student_data.get('avg_execution_time', 0), 1)}ms",
                    "max_memory_used": f"{round(student_data.get('max_memory_used_mb', 0), 2):.2f}MB",
                    "difficulty_score": student_data.get("difficulty_score", 0),
                    "img": f"/api/v1/pic?student_id={student_data.get('studentId', '')}"
                }
            
            # Only show student on their actual page to avoid duplicates
            if is_on_current_page:
                # Mark the current user in the existing leaderboard
                for item in result["leaderboard"]:
                    if item["student_id"] == student_id:
                        item["is_current_user"] = True
                        item["scroll_to_rank"] = True
                        break
        
        return result

# Cache warming function
def warm_cache():
    """Pre-warm cache with common queries"""
    common_queries = [
        ("batch", "PFS-888", "vijayawada", 1, 10),
        ("global", None, None, 1, 10),
        ("course", "PFS-888", "vijayawada", 1, 10)
    ]
    
    for mode, batch, location, page, limit in common_queries:
        try:
            UltraFastLeaderboard.get_leaderboard_ultra_fast(mode, batch, location, page, limit)
        except:
            pass