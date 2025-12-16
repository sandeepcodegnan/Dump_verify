from flask import request, jsonify
from flask_restful import Resource
from web.jwt.auth_middleware import student_required
from web.Exam.Flags.feature_flags import is_enabled, is_enabled_for_location, is_enabled_for_batch
from web.Exam.exam_central_db import student_collection

class CodePlaygroundFeatureCheck(Resource):
    @student_required
    def get(self):
        batch = request.args.get('batch')
        location = request.args.get('location')
        student_id = request.args.get('student_id')
        
        if not batch or not location or not student_id:
            return {
                "enabled": False,
                "message": "batch, location, and student_id parameters are required"
            }, 400
        

        student = (student_collection.find_one({"id": student_id, "location": location}) or 
                  student_collection.find_one({"_id": student_id, "location": location}) or
                  student_collection.find_one({"student_id": student_id, "location": location}))
        
        if not student:
            return {
                "enabled": False,
                "message": f"Student not found with id: {student_id} in location: {location}",
                "debug": "Check student ID field name in database"
            }, 404

        global_enabled = is_enabled("flagcodePlayground")
        location_enabled = is_enabled_for_location("flagcodePlayground", location) if global_enabled else False
        batch_enabled = is_enabled_for_batch("flagcodePlayground", batch, location)
        

        placed_status = student.get("placed")
        if placed_status == True:
            return {
                "enabled": False,
                "batch": batch,
                "location": location,
                "student_id": student_id,
                "flags": {
                    "global": global_enabled,
                    "location": location_enabled,
                    "batch": batch_enabled
                },
                "placed_status": placed_status,
                "message": "You are already placed!"
            }, 200
        
        
        return {
            "enabled": batch_enabled,
            "batch": batch,
            "location": location,
            "student_id": student_id,
            "flags": {
                "global": global_enabled,
                "location": location_enabled,
                "batch": batch_enabled
            },
            "message": self._get_status_message(global_enabled, location_enabled, batch_enabled)
        }, 200
    
    def _get_status_message(self, global_enabled, location_enabled, batch_enabled):
        if not global_enabled:
            return "Code Playground is disabled globally"
        elif not location_enabled:
            return "Code Playground is disabled for this location"
        elif not batch_enabled:
            return "Code Playground is disabled for this batch"
        else:
            return "Code Playground is enabled"