from flask_restful import Resource
from flask import request
from web.jwt.auth_middleware import exams_required
from web.Exam.exam_central_db import db


class PeriodsAPI(Resource):
    @exams_required
    def get(self):
        try:
            report_type = request.args.get("report_type")
            if not report_type or report_type not in ["weekly", "monthly"]:
                return {"success": False, "error": "Invalid or missing report_type (weekly/monthly)"}, 400
            period_ids = list(db["parent_message_status"].distinct("period_id", {"report_type": report_type}))
            period_ids.sort(reverse=True)
            return {"success": True, "report_type": report_type, "period_ids": period_ids, "count": len(period_ids)}, 200
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500
