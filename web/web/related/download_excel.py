from flask import Flask,jsonify,request,send_file
from flask_restful import Resource,abort
from web.jwt.auth_middleware import All_required
import pandas as pd
from io import BytesIO
from web.db.db_utils import get_collection

def get_student_collection():
    return get_collection('students')

collection = get_student_collection()

class DownloadAllStudents(Resource):
    def __init__(self):
        super().__init__()

    def get(self):
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
        if student_id_filter:
            query["studentId"] = {"$regex": student_id_filter, "$options": "i"}
        if student_name_filter:
            query["name"] = {"$regex": student_name_filter, "$options": "i"}
        if phone_filter:
            query["$or"] = query.get("$or", []) + [
                {"studentPhNumber": {"$regex": phone_filter, "$options": "i"}},
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
        if location_filter:
            query["location"] = {"$regex": location_filter, "$options": "i"}
        if placed_filter and placed_filter.strip():
            query["placed"] = placed_filter.lower() == 'true'
        if batch_filter:
            query["BatchNo"] = {"$regex": batch_filter, "$options": "i"}
        
        # Fetch data
        students = list(collection.find(query, {'_id': 0}))
        # print(f"Found {len(students)} records with query: {query}")
        
        # Create Excel
        if not students:
            students = [{'No Data': 'No records found'}]
        df = pd.DataFrame(students)
        
        # Define desired columns and handle missing ones
        desired_cols = ['studentId', 'name', 'email', 'BatchNo', 'studentPhNumber', 'department', 'parentNumber','collegeName','qualification','highestGraduationpercentage', 'yearOfPassing','TenthPassoutYear','tenthStandard','TwelfthPassoutYear','twelfthStandard', 'studentSkills', 'ArrearsCount', 'location', 'placed']
        for col in desired_cols:
            if col not in df.columns:
                df[col] = None
        df = df[desired_cols]
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students_List')
        output.seek(0)
        
        return send_file(output, 
                as_attachment=True, 
                download_name='students_List.xlsx', 
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')