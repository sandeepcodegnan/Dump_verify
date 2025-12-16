from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import serstd_required,multi_ABJP_required
from gridfs import GridFS
from web.student.search_student.central_functions import (
    build_search_query,
    build_fast_search_query,
    build_ultra_fast_query,
    find_student,
    find_student_for_details,
    validate_student_status,
    get_section_data,
    validate_request_params,
    handle_placed_student_response,
    build_section_response
)
from web.db.db_utils import get_collection, get_db

class Search_Students(Resource):
    # Constants
    VALID_SECTIONS = ['Student_Details', 'Applied_Jobs', 'Eligible_Jobs', 'Attendance_Overview', 'Exams_Details']
    
    def __init__(self):
        super().__init__()
        self.std_collection = get_collection('students')
        self.job_collection = get_collection('jobs')
        self.attend_collection = get_collection('attendance')
        self.batch_collection = get_collection('batches')
        self.db = get_db()
        self.fs = GridFS(self.db)
   

    @multi_ABJP_required
    def post(self):
        search = request.json.get('search')
        section = request.json.get('section', 'Student_Details')
        
        # Validate request parameters
        validation_error = validate_request_params(search, section, self.VALID_SECTIONS)
        if validation_error:
            return validation_error
        
        # Ultra-fast optimization for ALL sections
        ultra_query = build_ultra_fast_query(search)
        if ultra_query:
            # Try ultra-fast exact match first
            if section == 'Student_Details':
                student_data = find_student_for_details(self.std_collection, ultra_query)
            else:
                student_data = find_student(self.std_collection, ultra_query)
                
            if not student_data:
                # Fallback to fast search
                search_query = build_fast_search_query(search)
                if section == 'Student_Details':
                    student_data = find_student_for_details(self.std_collection, search_query)
                else:
                    student_data = find_student(self.std_collection, search_query)
        else:
            # No ultra-fast match possible, use appropriate search
            if section == 'Student_Details':
                search_query = build_fast_search_query(search)
                student_data = find_student_for_details(self.std_collection, search_query)
            else:
                search_query = build_search_query(search)
                student_data = find_student(self.std_collection, search_query)
            
        if not student_data:
            return {"error": "Student not found"}, 404
        
        std_id = student_data.get("studentId")
        
        # Validate student status
        validation_result = validate_student_status(student_data)
        if validation_result:
            if validation_result[0] == "PLACED_STUDENT":
                return handle_placed_student_response(section, student_data, std_id, self, request)
            else:
                return validation_result
        
        # Get section-specific data and build response
        section_data = get_section_data(section, student_data, std_id, self, request)
        response = build_section_response(section, section_data, student_data)
        
        return response, 200

    @serstd_required
    def get(self):
        search = request.args.get('search') or request.args.get('studentId')
        location = request.args.get('location')
        section = request.args.get('section', 'Student_Details')

        if not search:
            return {"error": "Search parameter (search or studentId) is required"}, 400
        
        # Validate section parameter
        if section not in self.VALID_SECTIONS:
            return {"error": f"Invalid section. Use: {', '.join(self.VALID_SECTIONS)}"}, 400

        # Ultra-fast optimization for ALL sections
        ultra_query = build_ultra_fast_query(search)
        if ultra_query:
            # Try ultra-fast exact match first
            final_ultra_query = ultra_query.copy()
            if location:
                if "$or" in final_ultra_query:
                    # For $or queries, wrap with $and
                    final_ultra_query = {"$and": [ultra_query, {"location": location}]}
                else:
                    final_ultra_query["location"] = location
                
            if section == 'Student_Details':
                student_data = find_student_for_details(self.std_collection, final_ultra_query)
            else:
                student_data = find_student(self.std_collection, final_ultra_query)
                
            if not student_data:
                # Fallback to fast search
                search_query = build_fast_search_query(search)
                if location:
                    if "$or" in search_query:
                        search_query = {"$and": [search_query, {"location": location}]}
                    else:
                        search_query["location"] = location
                    
                if section == 'Student_Details':
                    student_data = find_student_for_details(self.std_collection, search_query)
                else:
                    student_data = find_student(self.std_collection, search_query)
        else:
            # No ultra-fast match possible, use appropriate search
            if section == 'Student_Details':
                search_query = build_fast_search_query(search)
            else:
                search_query = build_search_query(search)
                
            if location:
                if "$or" in search_query:
                    search_query = {"$and": [search_query, {"location": location}]}
                else:
                    search_query["location"] = location
                    
            if section == 'Student_Details':
                student_data = find_student_for_details(self.std_collection, search_query)
            else:
                student_data = find_student(self.std_collection, search_query)
            
        if not student_data:
            return {"error": "Student not found"}, 404
        
        std_id = student_data.get("studentId")
        
        # Validate student status
        validation_result = validate_student_status(student_data)
        if validation_result:
            if validation_result[0] == "PLACED_STUDENT":
                return handle_placed_student_response(section, student_data, std_id, self, request)
            else:
                return validation_result
        
        # Get section-specific data and build response
        section_data = get_section_data(section, student_data, std_id, self, request)
        response = build_section_response(section, section_data, student_data)
        
        return response, 200