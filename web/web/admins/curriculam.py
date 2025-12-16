from flask import request,jsonify
from web.jwt.auth_middleware import admin_required
from flask_restful import Resource
from web.db.db_utils import get_collection
import uuid

class CurriCulum(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('curriculum')

    @admin_required
    def post(self):
        data = request.json  

        if isinstance(data, list):
            responses = []
            for item in data:
                subject = item.get('subject')
                day = item.get('dayOrder')
                topic = item.get('topic')
                subtopics = item.get('subTopics')
                id = str(uuid.uuid4())

                if not (subject and day and topic):
                    responses.append({"error": "Missing required fields", "data": item})
                    continue

                if self.collection.find_one({"DayOrder": day, "subject": subject}):  
                    responses.append({"error": "Data already exists", "data": item})
                    continue

                curriculam = {
                    "id": id,
                    "subject": subject,
                    "DayOrder": day,
                    "Topics": topic,
                    "SubTopics":subtopics
                }

                result = self.collection.insert_one(curriculam)
                curriculam['_id'] = str(result.inserted_id)

                responses.append({"message": "Curriculum Updated Successfully", "data": curriculam})

            return {"responses": responses}, 200

        elif isinstance(data, dict):
            subject = data.get('subject')
            day = data.get('dayOrder')
            topic = data.get('topic')
            subtopics = data.get('subTopics')
            id = str(uuid.uuid4())

            if not (subject and day and topic):
                return {"error": "Missing required fields"}, 400

            if self.collection.find_one({"DayOrder": day, "subject": subject}):  
                return {"error": "Data already exists"}, 409

            curriculam = {
                "id": id,
                "subject": subject,
                "DayOrder": day,
                "Topics": topic,
                "SubTopics":subtopics
            }

            result = self.collection.insert_one(curriculam)
            curriculam['_id'] = str(result.inserted_id)

            return {"message": "Curriculum Updated Successfully", "data": curriculam}, 200

        else:
            return {"error": "Invalid input format. Must be a dictionary or a list of dictionaries"}, 400
    @admin_required
    def get(self):
        Curriculum = list(self.collection.find({}))
        for data in Curriculum:
            data["_id"] = str(data["_id"])
        return {"message":"All Curriculums with location ","data": Curriculum}, 200