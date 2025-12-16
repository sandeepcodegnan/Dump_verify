from flask import Flask,jsonify,request
from flask_restful import Resource,abort
from web.jwt.auth_middleware import All_required
from web.db.db_utils import get_collection

def get_student_collection():
    return get_collection('students')
import logging

class GetAllStudents(Resource):
    def __init__(self):
        super().__init__()
        self.student_collection = get_student_collection()
        self.logger = logging.getLogger(__name__)

    @All_required    
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            skip = (page - 1) * limit
            
            # Search functionality
            search = request.args.get('search')
            
            # Filter parameters
            student_id_filter = request.args.get('studentId')
            student_name_filter = request.args.get('name')
            phone_filter = request.args.get('studentPhNumber')
            department_filter = request.args.get('department')
            highest_graduation_filter = request.args.get('highestGraduationpercentage')
            yop_filter = request.args.get('yearOfPassing')
            backlogs_filter = request.args.get('ArrearsCount')
            location_filter = request.args.get('location')
            placed_filter = request.args.get('placed')
            batch_filter = request.args.get('BatchNo')
            
            # Build query
            query = {}
            
            # Add search conditions
            if search:
                search_conditions = [
                    {"id": {"$regex": search, "$options": "i"}},
                    {"studentId": {"$regex": search, "$options": "i"}},
                    {"name": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}},
                    {"studentPhNumber": {"$regex": search, "$options": "i"}},
                    {"parentNumber": {"$regex": search, "$options": "i"}},
                    {"BatchNo": {"$regex": search, "$options": "i"}},
                    {"collegeName": {"$regex": search, "$options": "i"}},
                    {"qualification": {"$regex": search, "$options": "i"}},
                    {"department": {"$regex": search, "$options": "i"}},
                    {"location": {"$regex": search, "$options": "i"}},
                    {"studentSkills": {"$regex": search, "$options": "i"}}
                ]
                query["$or"] = search_conditions
            
            # Add filters
            if student_id_filter:
                query["studentId"] = {"$regex": student_id_filter, "$options": "i"}
            if student_name_filter:
                query["name"] = {"$regex": student_name_filter, "$options": "i"}
            if phone_filter:
                query["$or"] = query.get("$or", []) + [
                    {"studentPhNumber": {"$regex": phone_filter, "$options": "i"}},
                    {"parentNumber": {"$regex": phone_filter, "$options": "i"}}
                ]
            if department_filter:
                departments = [dept.strip() for dept in department_filter.split(',')]
                dept_conditions = [{"department": {"$regex": dept, "$options": "i"}} for dept in departments]
                if len(dept_conditions) == 1:
                    query["department"] = {"$regex": departments[0], "$options": "i"}
                else:
                    query["$or"] = query.get("$or", []) + dept_conditions
            if highest_graduation_filter:
                query["highestGraduationpercentage"] = {"$gte": float(highest_graduation_filter)}
            if yop_filter:
                query["yearOfPassing"] = yop_filter
            if backlogs_filter:
                query["ArrearsCount"] = backlogs_filter
            if location_filter and location_filter.lower() != 'all':
                query["location"] = {"$regex": location_filter, "$options": "i"}
            if placed_filter:
                query["placed"] = placed_filter.lower() == 'true'
            if batch_filter:
                query["BatchNo"] = {"$regex": batch_filter, "$options": "i"}
            
            total_count = self.student_collection.count_documents(query)
            student_document = list(self.student_collection.find(query,{"_id":1,"id":1,"studentId":1, "name":1,"BatchNo":1,"email":1, "studentPhNumber":1,"parentNumber":1,"collegeName":1,"qualification":1,"department":1,"highestGraduationpercentage":1,"TenthPassoutYear":1,"tenthStandard":1,"TwelfthPassoutYear":1,"twelfthStandard":1,"yearOfPassing":1,"studentSkills":1,"ArrearsCount":1,"location":1,"placed":1}).skip(skip).limit(limit))
            
            for data in student_document:
                data['_id'] = str(data['_id'])
            
            return jsonify({
                "data": student_document,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit
                }
            })

        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            abort(500, message="Internal server error.")
    

    