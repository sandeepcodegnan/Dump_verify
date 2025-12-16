from datetime import datetime
from web.Exam.exam_central_db import db, student_collection as students_coll

metrics_coll = db.student_leaderboard_metrics

def parse_performance(perf_str, unit):
    """Parse performance strings like '25.5ms' or '1.2MB'"""
    if unit in perf_str:
        return float(perf_str.replace(unit, ""))
    return 0

def format_time(seconds):
    """Format seconds to 'Xm Ys' format"""
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

def update_student_metrics(student_id, question_data):
    try:
        from web.Exam.exam_central_db import codeplayground_collection
        
        student = students_coll.find_one({"id": student_id}, 
                                       {"name": 1, "studentId": 1, "BatchNo": 1, "location": 1})
        if not student:
            return
            
        # Recalculate all metrics from scratch for this student
        submissions = list(codeplayground_collection.find({"id": student_id}))
        if not submissions:
            return
            
        # Group by questionId and get best submission for each question
        question_best = {}
        total_time_spent = 0
        total_submissions = len(submissions)
        best_exec_times = []
        best_memory_usage = []
        
        for submission in submissions:
            question_id = submission.get("questionId")
            awarded_score = submission.get("awarded_score", 0)
            max_score = submission.get("max_score", 0)
            time_spent = submission.get("time_tracking", {}).get("total_time_spent", 0)
            
            total_time_spent += time_spent
            
            # Keep best score for each question
            if question_id not in question_best or awarded_score > question_best[question_id]["awarded_score"]:
                overall_perf = submission.get("overall_performance", {})
                avg_exec_time = parse_performance(overall_perf.get("avg_execution_time", "0ms"), "ms")
                
                max_memory_str = overall_perf.get("max_memory_used", "0KB")
                if "MB" in max_memory_str:
                    max_memory_mb = parse_performance(max_memory_str, "MB")
                else:
                    max_memory_mb = parse_performance(max_memory_str, "KB") / 1024
                
                question_best[question_id] = {
                    "awarded_score": awarded_score,
                    "max_score": max_score,
                    "difficulty": submission.get("difficulty", "Easy"),
                    "exec_time": avg_exec_time,
                    "memory_mb": max_memory_mb
                }
        
        # Calculate final metrics from best submissions only
        total_score = sum(q["awarded_score"] for q in question_best.values())
        questions_solved = sum(1 for q in question_best.values() if q["awarded_score"] == q["max_score"])
        
        # Collect performance metrics only from best submissions
        for q in question_best.values():
            if q["exec_time"] > 0:
                best_exec_times.append(q["exec_time"])
            if q["memory_mb"] > 0:
                best_memory_usage.append(q["memory_mb"])
        
        # Difficulty breakdown
        difficulty_breakdown = {"easy": 0, "medium": 0, "hard": 0}
        difficulty_score = 0
        difficulty_weights = {"Easy": 1, "Medium": 2, "Hard": 3}
        
        for q in question_best.values():
            if q["awarded_score"] == q["max_score"]:
                diff = q["difficulty"].lower()
                if diff in difficulty_breakdown:
                    difficulty_breakdown[diff] += 1
                difficulty_score += difficulty_weights.get(q["difficulty"], 1)
        
        avg_execution_time = sum(best_exec_times) / len(best_exec_times) if best_exec_times else 0
        max_memory_used_mb = max(best_memory_usage) if best_memory_usage else 0
        
        # Replace entire document with correct metrics
        metrics_coll.replace_one(
            {"student_id": student_id},
            {
                "student_id": student_id,
                "studentId": student.get("studentId"),
                "name": student.get("name"),
                "batchNo": student.get("BatchNo"),
                "location": student.get("location"),
                "total_score": total_score,
                "questions_solved": questions_solved,
                "difficulty_breakdown": difficulty_breakdown,
                "total_time_spent": total_time_spent,
                "avg_execution_time": avg_execution_time,
                "max_memory_used_mb": max_memory_used_mb,
                "difficulty_score": difficulty_score,
                "total_submissions": total_submissions,
                "last_updated": datetime.utcnow()
            },
            upsert=True
        )
        
    except Exception as e:
        print(f"Error updating metrics for {student_id}: {e}")

def build_filter_query(mode, batch_no, location):
    """Build MongoDB filter query based on mode"""
    if mode == 'batch':
        return {"batchNo": batch_no, "location": location}, f"Batch {batch_no} - {location}"
    elif mode == 'course':
        course_code = batch_no.split('-')[0]
        return {"batchNo": {"$regex": f"^{course_code}-"}, "location": location}, f"Course {course_code} - {location} (All Batches)"
    elif mode == 'global':
        return {}, "Global (All Locations)"
    else:
        raise ValueError("Invalid mode")

def build_rank_item(item, position):
    """Build individual rank item for response"""
    return {
        "position": position,
        "name": item.get("name", ""),
        "batchNo": item.get("batchNo", ""),
        "location": item.get("location", ""),
        "total_score": item.get("total_score", 0),
        "questions_solved": item.get("questions_solved", 0),
        "difficulty_breakdown": item.get("difficulty_breakdown", {"easy": 0, "medium": 0, "hard": 0}),
        "total_time_spent": format_time(item.get("total_time_spent", 0)),
        "avg_execution_time": f"{round(item.get('avg_execution_time', 0), 1)}ms",
        "max_memory_used": f"{round(item.get('max_memory_used_mb', 0), 2):.2f}MB",
        "difficulty_score": item.get("difficulty_score", 0),
        "img": f"/api/v1/pic?student_id={item.get('studentId', '')}"
    }

def get_student_rank(filter_query, student_id, limit):
    """Get student's rank and page information"""
    rank_pipeline = [
        {"$match": filter_query},
        {"$sort": {"total_score": -1, "avg_execution_time": 1, "total_time_spent": 1, "max_memory_used_mb": 1, "questions_solved": -1}},
        {"$group": {"_id": 1, "students": {"$push": "$student_id"}}},
        {"$project": {"_id": 0, "students": 1}}
    ]
    
    rank_result = list(metrics_coll.aggregate(rank_pipeline))
    if not rank_result or "students" not in rank_result[0]:
        return None
        
    student_ids = rank_result[0]["students"]
    if student_id not in student_ids:
        return None
        
    pos = student_ids.index(student_id) + 1
    student_page = ((pos - 1) // limit) + 1
    
    return {
        "student_id": student_id,
        "rank": pos,
        "page": student_page,
        "position": pos
    }

# This function is deprecated - use ultra_fast_leaderboard.py instead
def get_leaderboard_fast(mode, batch_no=None, location=None, page=1, limit=10, student_id=None):
    from web.Exam.codeplayground.ultra_fast_leaderboard import UltraFastLeaderboard
    return UltraFastLeaderboard.get_leaderboard_ultra_fast(mode, batch_no, location, page, limit, student_id)

def create_leaderboard_indexes():
    try:
        indexes = [
            ([("total_score", -1), ("avg_execution_time", 1), ("total_time_spent", 1), ("max_memory_used_mb", 1), ("questions_solved", -1)], "idx_leaderboard_sort"),
            ([("batchNo", 1), ("location", 1)], "idx_batch_location"),
            ([("student_id", 1)], "idx_student_id"),
            ([("batchNo", 1)], "idx_batch")
        ]
        
        existing_indexes = set(metrics_coll.list_indexes())
        existing_names = {idx.get('name') for idx in existing_indexes}
        
        for index_spec, name in indexes:
            if name not in existing_names:
                try:
                    metrics_coll.create_index(index_spec, name=name, unique=(name == "idx_student_id"))
                except Exception as idx_error:
                    # Silently ignore index creation errors to avoid spam
                    pass
            
    except Exception as e:
        # Silently ignore to avoid log spam
        pass