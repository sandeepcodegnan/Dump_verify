from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import leaderbd_required
from web.Exam.codeplayground.ultra_fast_leaderboard import UltraFastLeaderboard, warm_cache
from web.Exam.codeplayground.leaderboard_metrics import create_leaderboard_indexes

def parse_request_data():
    if request.is_json:
        return request.get_json(force=True) or {}
    if request.args:
        return request.args.to_dict()
    if request.form:
        return request.form.to_dict()
    return {}

def error_response(message, status_code=400):
    return {"success": False, "message": message}, status_code

class Leaderboard(Resource):
    def __init__(self):
        create_leaderboard_indexes()
        try:
            warm_cache()
        except:
            pass
        super().__init__()
    
    @leaderbd_required
    def get(self):
        try:
            args = parse_request_data()
            mode = args.get('mode', '').lower()
            batch_no = args.get('batchNo', '').strip()
            location = args.get('location', '').strip()
            limit = min(int(args.get('limit', 10)), 100)
            page = max(int(args.get('page', 1)), 1)
            student_id = args.get('studentId', '').strip()
            
            if mode not in ['batch', 'course', 'global']:
                return error_response("'mode' must be one of: batch, course, global", 400)
            
            # Use ultra-fast leaderboard
            result, status_code = UltraFastLeaderboard.get_leaderboard_ultra_fast(
                mode=mode,
                batch_no=batch_no,
                location=location,
                page=page,
                limit=limit,
                student_id=student_id if student_id else None
            )
            
            return result, status_code
            
        except Exception as e:
            print(f"Leaderboard error: {str(e)}")
            return error_response("Leaderboard service temporarily unavailable", 503)