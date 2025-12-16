from flask import request, jsonify
from flask_restful import Resource
from web.jwt.auth_middleware import multiple_required
from pymongo import ASCENDING
from web.db.db_utils import get_collection

def get_batches_collection():
    return get_collection('batches')

COLL = get_batches_collection()


# ────────────────────────── Helper
def error_response(msg: str, code: int = 400):
    r = jsonify({"success": False, "message": msg})
    r.status_code = code
    return r


# ────────────────────────── Resource
class ActiveBatches(Resource):
    """Returns all active batches (no pagination)."""
    
    @multiple_required
    def get(self):
        try:
            # -------- Base filter
            q = {"Status": "Active"}

            # Location filter (optional, exact case-insensitive)
            loc = request.args.get("location")
            if loc:
                q["location"] = {"$regex": f"^{loc}$", "$options": "i"}

            # Course filter (optional, substring case-insensitive)
            course = request.args.get("course")
            if course:
                q["Course"] = {"$regex": course, "$options": "i"}

            projection = {
                "_id": 0,
                "Batch": 1,
                "Course": 1,
                "location": 1,
                "Status": 1,
                "id": 1,
                "Duration": 1,
                "StartDate": 1,
                "EndDate": 1,
            }

            cursor = (
                COLL.find(q, projection)
                .sort("Batch", ASCENDING)   # alphabetical
            )

            data = list(cursor)

            return jsonify(
                {
                    "success": True,
                    "count": len(data),
                    "data": data,
                }
            )

        except Exception as exc:
            return error_response(f"Internal server error: {exc}", 500)
