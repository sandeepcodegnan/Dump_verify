from flask_restful import Resource
from web.jwt.auth_middleware import AdminResource,admin_required
from web.Exam.Parent_Reports.Parent_Whatsapp_report.async_processor import async_processor


class TaskStatusAPI(Resource):
    @admin_required
    def get(self, task_id):
        try:
            result = async_processor.get_task_status(task_id)
            if "error" in result and result["error"]:
                return {"success": False, "error": result["error"]}, 404
            return {"success": True, "task": result}, 200
        except Exception as e:
            return {"success": False, "error": f"Internal server error: {str(e)}"}, 500
