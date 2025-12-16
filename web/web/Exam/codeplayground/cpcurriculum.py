from flask import request
from web.jwt.auth_middleware import student_required
from flask_restful import Resource
from web.Exam.exam_central_db import db
from web.Exam.Flags.feature_flags import is_enabled

class cpcurriculum(Resource):
    def __init__(self):
        super().__init__()
  
    @student_required
    def get(self):
        if not is_enabled("flagcodePlayground"):
            return {"error": "Code playground feature is disabled"}, 404
            
        subject = request.args.get('subject')
        location = request.args.get('location')
        batch = request.args.get('batchNo')

        if not (subject and location and batch) :
            return {"error": "Missing required fields"}, 400    
        
        docs = list(db.Mentor_Curriculum_Table.find({"subject": subject, "batch": batch,"location":location}))
        if not docs:
            return {"error": "No curriculum found for the given subject, batch, and location"}, 404
        
        # Get all available tags in one query for performance
        code_coll = f"{subject.lower()}_code_codeplayground"
        available_tags = set(tag.lower() for tag in db[code_coll].distinct("Tags"))
        
        result = []
        for doc in docs:
            curriculum_table = {}
            for curriculum_id, curriculum in doc.get("curriculumTable", {}).items():
                filtered_subtopics = []
                
                for st in curriculum.get("SubTopics", []):
                    if st["tag"].lower() in available_tags:
                        filtered_subtopics.append({"title": st["title"], "tag": st["tag"]})
                
                if filtered_subtopics:
                    # Sort by day number extracted from tag (Day-X:Y)
                    filtered_subtopics.sort(key=lambda x: int(x["tag"].split("-")[1].split(":")[0]))
                    
                    curriculum_table[curriculum_id] = {
                        "subject": curriculum.get("subject"),
                        "Topics": curriculum.get("Topics"),
                        "SubTopics": filtered_subtopics
                    }
            
            result.append({"curriculumTable": curriculum_table})
        
        return {"message":"Daily classes Curriculum","std_curiculum":result},200