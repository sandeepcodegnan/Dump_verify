from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from web.db.db_utils import get_collection


class ListofStudentsForMentor(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('schedule')
        self.student_collection = get_collection('students')
        self.mentor_collection = get_collection('mentors')

    @mentor_required
    def get(self):
        mentorId = request.args.get('mentorId')
        location = request.args.get('location')
        batch = request.args.get('batch')
        student_id = request.args.get('studentId')
        student_name = request.args.get('name')
        all_batches = request.args.get('allBatches', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

      
        schedule_data = list(self.collection.find({"$and":[{"MentorId":mentorId},{"location":location}]},{"password":0}))
        dat = []
        for data in schedule_data:
            data["_id"] = str(data["_id"])
            if all_batches:
                for batch_no in data['batchNo']:
                    dat.append(batch_no)
            elif batch:
                if batch in data['batchNo']:
                    dat.append(batch)

        mentor_data = list(self.mentor_collection.find({"$and":[{"id":mentorId},{"location":location}]},{"password":0}))
        for mentor in mentor_data:
            mentor["_id"] = str(mentor["_id"])

        # Build student filter
        student_filter = {"location": location}
        if dat:
            student_filter["BatchNo"] = {"$in": dat}
        if student_id:
            student_filter["studentId"] = {"$regex": student_id, "$options": "i"}
        if student_name:
            student_filter["name"] = {"$regex": student_name, "$options": "i"}

        total_students = self.student_collection.count_documents(student_filter)
        students = list(self.student_collection.find(student_filter, {"_id":1,"studentId":1, "name":1,"BatchNo":1,"email":1, "studentPhNumber":1,"collegeName":1,"qualification":1,"department":1,"highestGraduationpercentage":1,"yearOfPassing":1,"studentSkills":1,"ArrearsCount":1,"location":1}).skip(skip).limit(limit))
        
        student_data = []
        for data in students:
            data["_id"] = str(data["_id"])
            student_data.append(data)

        total_pages = (total_students + limit - 1) // limit

        return {"message":"Getting All batches data",
                "schedule_data":schedule_data,
                "mentor_data":mentor_data,
                "student_data":student_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_students": total_students,
                    "limit": limit
                }},200

