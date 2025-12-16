from flask import request, g
from web.Exam.Flags.feature_flags import is_enabled, is_enabled_for_location, is_enabled_for_batch
from web.Exam.exam_central_db import student_collection

def check_codeplayground_access():
    batch = request.args.get('batch') or request.args.get('batchNo') or request.headers.get('X-Batch')
    location = request.args.get('location') or request.headers.get('X-Location')
    
    if not is_enabled("flagcodePlayground"):
        return {"message": "Code Playground feature is globally disabled"}, 503
    
    if location and not is_enabled_for_location("flagcodePlayground", location):
        return {"message": f"Code Playground feature is disabled for {location}"}, 503
    
    if batch and location:
        if not is_enabled_for_batch("flagcodePlayground", batch, location):
            return {"message": f"Code Playground feature is disabled for batch {batch}"}, 503
    
    student_id = request.args.get('student_id') or request.args.get('studentId') or request.headers.get('X-Student-ID')
    if student_id and location:
        student = student_collection.find_one({"id": student_id, "location": location})
        if student and student.get("placed") == True:
            return {"message": "You are already placed!"}, 403
    
    g.batch = batch
    g.location = location
    g.feature_enabled = True
    
    return None

def create_feature_aware_resource(resource_class):
    class FeatureAwareResource(resource_class):
        def dispatch_request(self, *args, **kwargs):
            feature_check = check_codeplayground_access()
            if feature_check:
                return feature_check
            return super().dispatch_request(*args, **kwargs)
    
    FeatureAwareResource.__name__ = f"FeatureAware{resource_class.__name__}"
    return FeatureAwareResource