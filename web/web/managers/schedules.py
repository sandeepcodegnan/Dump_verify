import uuid
from flask import Flask, request
from flask_restful import Resource
from web.jwt.auth_middleware import multiple_required,manager_required
from web.db.db_utils import get_collection, get_db


class ScheduleBatches(Resource):
    def __init__(self):
        super().__init__()
        self.schedule_collection = get_collection('schedule')
        self.mentor_collection = get_collection('mentors')
        self.mentor_curriculum_collection = get_collection('mentor_curriculum_table')
        self.pratice_mentor = get_collection('practice_mentors')
        self.batches_collection = get_collection('batches')
        self.db = get_db()

    @manager_required
    def post(self):
        data = request.get_json()
        course = data.get('techStack')
        batches = data.get('batches')
        subject = data.get('subject')
        mentor_name = data.get('mentorName')
        room_no = data.get('roomNo')
        start = data.get('startTime')
        end = data.get('endTime')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        location = data.get('location')
        mentor_id = data.get('mentorId')
        UserType = data.get('userType')
        
        # Generate a unique id for the schedule entry.
        schedule_id = str(uuid.uuid4())
        
        if not (course and batches and subject and location):
            return {"error": "Missing required fields for schedule"}, 400
        
        # Normalize batches to ensure consistent format
        if isinstance(batches, str):
            batches = [batch.strip() for batch in batches.split(",") if batch.strip()]
        batches = [str(batch).strip() for batch in batches]
        
        # Check mentor exists in either collection
        pmentor = None
        mentor = None
        if mentor_id:
            pmentor = self.pratice_mentor.find_one({"id": mentor_id})
            mentor = self.mentor_collection.find_one({"id": mentor_id})
            
            if not pmentor and not mentor:
                return {"error": "Mentor not found"}, 404
        
        # Determine mentor type for validation
        is_practice_mentor = pmentor and pmentor.get('usertype') == 'Practice_Mentors'
        
        # Continue with validation logic for active/upcoming batches
        time_overlap_condition = {
            "$or": [
                {"$and": [{"StartTime": {"$lt": start}}, {"EndTime": {"$gt": start}}]},  # New start time is strictly inside an existing slot
                {"$and": [{"StartTime": {"$gt": start}}, {"StartTime": {"$lt": end}}]},  # Existing start time is strictly inside new slot
                {"$and": [{"StartTime": {"$lt": end}}, {"EndTime": {"$gt": end}}]}  # New end time is strictly inside an existing slot
            ] }
        
        # Check for same mentor type conflicts only
        existing_schedule = self.schedule_collection.find_one({
            "$and": [
                {"subject": subject},
                {"batchNo": {"$in": batches}},
                {"MentorName": mentor_name},
                {"StartDate": start_date},
                {"EndDate": end_date},
                time_overlap_condition
            ]})
        
        if existing_schedule:
            return {"error": "For this batch, this subject already exists with a mentor in the given time slot"}, 404
        
        # Allow same batch for different mentor types, but check same type conflicts
        if is_practice_mentor:
            # For practice mentors, check conflicts with other practice mentors only
            existing_practice = self.schedule_collection.find_one({
                "$and": [
                    {"subject": subject},
                    {"batchNo": {"$in": batches}},
                    {"UserType": "Practice_Mentors"},
                    {"location": location}
                ]})
            if existing_practice:
                return {"error": "For this batch, a practice mentor already exists at this location"}, 404
        else:
            # For regular mentors, check conflicts with other regular mentors only
            existing_regular = self.schedule_collection.find_one({
                "$and": [
                    {"subject": subject},
                    {"batchNo": {"$in": batches}},
                    {"UserType": {"$ne": "Practice_Mentors"}},
                    {"location": location},
                    {"StartDate": start_date},
                    {"EndDate": end_date},
                    time_overlap_condition
                ]})
            if existing_regular:
                return {"error": "For this batch, a regular mentor already exists at this location"}, 404

        if self.schedule_collection.find_one({
            "$and": [
                {"RoomNo": room_no},
                {"location": location},
                {"MentorName": mentor_name},
                {"StartDate":start_date},
                {"EndDate":end_date},
                time_overlap_condition  
            ]}):
            return {"error": "For this day time slot, the room is already assigned for another class"}, 404

        # Create schedule
        schedule = {
            "id": schedule_id,
            "course": course,
            "batchNo": batches,
            "subject": subject,
            "MentorName": mentor_name,
            "RoomNo": room_no,
            "StartDate": start_date,
            "EndDate": end_date,
            "StartTime": start,
            "EndTime": end,
            "location": location,
            "MentorId": mentor_id,
            "UserType": UserType
        }
        result = self.schedule_collection.insert_one(schedule)
        schedule['_id'] = str(result.inserted_id)
        
        # If practice mentor, return early without curriculum
        if mentor_id and pmentor and pmentor.get('usertype') == 'Practice_Mentors':
            return {"message": "Schedule created. For Practice_Mentor, you don't need Curriculum"}, 200

        # ----------------- Mentor Curriculum Table Creation ----------------- #
        if not batches or not mentor_id or not subject:
            curriculum_response = {"error": "Missing required fields for mentor curriculum table: batches, mentorId, subject."}
        else:

            if isinstance(batches, str):
                batches = [batch.strip() for batch in batches.split(",") if batch.strip()]

            # Fetch curriculum documents based on subject.
            curriculum_documents = list(self.db.Curriculum.find(
                {"subject": subject},
                {"subject": 1, "Topics": 1, "SubTopics": 1, "DayOrder": 1}
            ))
            
            # Sort by extracting day number from DayOrder field
            def extract_day_number(doc):
                day_order = doc.get("DayOrder", "Day-0")
                try:
                    return int(day_order.split("-")[1])
                except (IndexError, ValueError):
                    return 0
            
            curriculum_documents.sort(key=extract_day_number)

            # Build the curriculum table structure in order.
            from collections import OrderedDict
            curriculum_table = OrderedDict()
            for doc in curriculum_documents:
                day_order = doc.get("DayOrder", "Day-Unknown")
                subtopics_array = []
                for index, subtopic in enumerate(doc.get("SubTopics", [])):
                    subtopics_array.append({
                        "title": subtopic,
                        "status": "false",
                        "tag": f"{day_order}:{index+1}"
                    })
                curriculum_table[str(doc["_id"])] = {
                    "subject": doc.get("subject"),
                    "Topics": doc.get("Topics"),
                    "SubTopics": subtopics_array
                }

            mentor_curriculum_docs = []
            for batch in batches:
                exists = self.mentor_curriculum_collection.find_one({
                    "mentorId": mentor_id,
                    "subject": subject,
                    "batch": batch
                })
                if not exists:
                    new_doc = {
                        "mentorId": mentor_id,
                        "mentorName":mentor_name,
                        "subject": subject,
                        "batch": batch,
                        "location":location,
                        "curriculumTable": curriculum_table
                    }
                    mentor_curriculum_docs.append(new_doc)

            if mentor_curriculum_docs:
                self.mentor_curriculum_collection.insert_many(mentor_curriculum_docs)
                inserted_docs = list(self.mentor_curriculum_collection.find({
                    "mentorId": mentor_id,
                    "subject": subject,
                    "batch": {"$in": batches}
                }))
                for doc in inserted_docs:
                    doc["_id"] = str(doc["_id"])
                curriculum_response = {
                    "inserted_data": inserted_docs,
                    "message": "Curriculum has been assigned to mentor Successfully."
                }
            else:
                curriculum_response = {
                    "message": "No new mentor curriculum(s) were created. All documents already exist."
                }

        return {
            "message": "New Batch Added Successfully!",
            "schedule_data": schedule,
            "mentor_curriculum": curriculum_response
        }, 200
    
    @multiple_required
    def get(self):
        location = request.args.get('location')
       
        if location == 'all':
            mentor_data = list(self.mentor_collection.find({}, {"password": 0}))
            for data in mentor_data:
                data["_id"] = str(data["_id"])
            practice_mentor = list(self.pratice_mentor.find({}, {"password": 0}))
            for datas in practice_mentor:
                datas["_id"] = str(datas["_id"])
            return {
                "message": "Getting all scheduled data",
                "mentor_data": mentor_data,
                "practice_mentor": practice_mentor
            }, 200
        else:
            mentor_data = list(self.mentor_collection.find({"location": location},{"password": 0}))
            for data in mentor_data:
                data["_id"] = str(data["_id"])
            practice_mentor = list(self.pratice_mentor.find({}, {"password": 0}))
            for datas in practice_mentor:
                datas["_id"] = str(datas["_id"])
            return {
                "message": f"Getting scheduled data for location: {location}",
                "mentor_data": mentor_data,
                "practice_mentor": practice_mentor
            }, 200

    def put(self):
        data = request.get_json()
        schedule_id = data.get("id")
        if not schedule_id:
            return {"error": "ID is required to update a record"}, 400

        schedule_doc = self.schedule_collection.find_one({"id": schedule_id})
        if not schedule_doc:
            return {"error": "Schedule with the specified ID not found"}, 404

        update_fields = {}
        if "roomNo" in data:
            update_fields["RoomNo"] = data["roomNo"]
        if "startDate" in data:
            update_fields["StartDate"] = data["startDate"]
        if "endDate" in data:
            update_fields["EndDate"] = data["endDate"]
        if "startTime" in data:
            update_fields["StartTime"] = data["startTime"]
        if "endTime" in data:
            update_fields["EndTime"] = data["endTime"]

        if update_fields:
            self.schedule_collection.update_one({"id": schedule_id}, {"$set": update_fields})

        updated_schedule = self.schedule_collection.find_one({"id": schedule_id})
        updated_schedule["_id"] = str(updated_schedule["_id"])

        return {
            "message": "Schedule updated successfully",
            "schedule": updated_schedule
        }, 200

    def delete(self):
        # First, retrieve the schedule document based on the provided id.
        schedule_id = request.args.get('id')
        if not schedule_id:
            return {"error": "ID is required to delete a record"}, 400

        schedule_doc = self.schedule_collection.find_one({"id": schedule_id})
        if not schedule_doc:
            return {"error": "Schedule with the specified ID not found"}, 404

        # Delete the schedule document.
        result = self.schedule_collection.delete_one({"id": schedule_id})
        if result.deleted_count == 0:
            return {"error": "Schedule with the specified ID not found"}, 404

        # Also delete the corresponding Mentor Curriculum Table document(s)
        # using mentorId, subject, and batchNo from the schedule.
        mentor_id = schedule_doc.get("MentorId")
        subject = schedule_doc.get("subject")
        batches = schedule_doc.get("batchNo")
        # Ensure batches is a list.
        if isinstance(batches, str):
            batches = [batches]
        mentor_curr_result = self.mentor_curriculum_collection.delete_many({
            "mentorId": mentor_id,
            "subject": subject,
            "batch": {"$in": batches}
        })

        return {
            "message": "Schedule and corresponding Mentor Curriculum Table deleted successfully",
            "deleted_schedule_id": schedule_id,
            "mentor_curriculum_deleted_count": mentor_curr_result.deleted_count
        }, 200
