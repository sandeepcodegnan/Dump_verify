import logging
from flask import request, jsonify
from flask_restful import Resource, abort
from web.jwt.auth_middleware import student_required
from web.db.db_utils import get_collection

def get_student_collection():
    return get_collection('students')
from bson import ObjectId


# Helper function to convert MongoDB document to JSON-compatible format
def to_json_compatible(data):
    if isinstance(data, dict):
        return {k: to_json_compatible(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [to_json_compatible(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

class GetStudentDetails(Resource):
    def __init__(self):
        super().__init__()
        self.student_collection = get_student_collection()
        self.logger = logging.getLogger(__name__)
        
    @student_required
    def get(self):
        student_id = request.args.get('student_id')
        location = request.args.get('location')
        
        if not student_id:
            self.logger.error("Invalid input: 'student_id' is missing.")
            abort(400, message="Invalid input: 'student_id' is required.")

        try:
            student_document = self.student_collection.find_one({"$and":[{"id": student_id},{"location":location}]},{"password":0})

            if not student_document:
                self.logger.info(f"Student with ID {student_id} not found.")
                abort(404, message="Student not found.")

            return jsonify(to_json_compatible(student_document))

        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            abort(500, message="Internal server error.")

        return jsonify({"error": "Unknown error occurred."}), 500