from flask import request, send_file
from flask_restful import Resource
from web.jwt.auth_middleware import manager_required
from web.db.db_utils import get_collection
from datetime import datetime, timedelta
import pandas as pd
import io

class DownloadAttendance(Resource):
    def __init__(self):
        super().__init__()
        self.collection = get_collection('attendance')
        self.student_collection = get_collection('student_login_details')
    @manager_required
    def get(self):
        location = request.args.get('location')
        
        if not location:
            return {"error": "Missing required field: location"}, 400

        query = {"location": location}

        # Use aggregation pipeline for better performance
        pipeline = [
            {"$match": query},
            {"$unwind": "$students"},
            {"$project": {
                "course": 1,
                "datetime": 1,
                "batchNo": 1,
                "studentId": "$students.studentId",
                "studentName": "$students.name",
                "status": "$students.status"
            }},
            {"$group": {
                "_id": {"course": "$course", "studentId": "$studentId"},
                "studentName": {"$first": "$studentName"},
                "batchNo": {"$first": "$batchNo"},
                "dates": {"$push": "$datetime"},
                "present_dates": {"$push": {"$cond": [{"$eq": ["$status", "present"]}, "$datetime", None]}}
            }}
        ]
        
        attendance_data = list(self.collection.aggregate(pipeline))
        
        if not attendance_data:
            available_batches = self.collection.distinct("batchNo", {"location": location})
            return {"error": f"No attendance records found for location: {location}. Available batches: {available_batches}"}, 404
        
        # Group by subject and get student IDs
        subjects_data = {}
        all_student_ids = set()
        
        for record in attendance_data:
            subject = record['_id']['course']
            student_id = record['_id']['studentId']
            
            if subject not in subjects_data:
                subjects_data[subject] = {}
            
            present_dates = [d for d in record['present_dates'] if d is not None]
            all_dates = record['dates']
            
            subjects_data[subject][student_id] = {
                'name': record['studentName'],
                'batchNo': record['batchNo'],
                'present_dates': set(present_dates),
                'all_dates': set(all_dates)
            }
            all_student_ids.add(student_id)
        
        # Get phone numbers efficiently
        student_phones = {}
        if all_student_ids:
            student_records = list(self.student_collection.find(
                {"studentId": {"$in": list(all_student_ids)}}, 
                {"studentId": 1, "studentPhNumber": 1, "parentNumber": 1}
            ))
            student_phones = {s['studentId']: {
                'studentPhNumber': s.get('studentPhNumber', ''),
                'parentNumber': s.get('parentNumber', '')
            } for s in student_records}
        
        all_student_records = []
        
        for subject_name, students in subjects_data.items():
            for student_id, data in students.items():
                all_dates = sorted(data['all_dates'])
                present_dates = data['present_dates']
                
                # Get past 3 days from current date, skipping Sundays
                current_date = datetime.now()
                past_3_days = []
                days_back = 1
                while len(past_3_days) < 3:
                    check_date = current_date - timedelta(days=days_back)
                    if check_date.weekday() != 6:  # Skip Sunday (weekday 6)
                        past_3_days.append(check_date.strftime('%Y-%m-%d'))
                    days_back += 1
                recent_dates = [d for d in all_dates if d in past_3_days]
                
                # Find missing dates in the target range (past 3 days)
                missing_dates = [d for d in sorted(recent_dates,reverse=True) if d not in present_dates]
                
                # Include only students who are missing all 3 days
                if len(recent_dates) >= 2 and len(missing_dates) >= 2:
                    phone_data = student_phones.get(student_id, {'studentPhNumber': '', 'parentNumber': ''})
                    recent_present = len([d for d in recent_dates if d in present_dates])
                    recent_absent = len(recent_dates) - recent_present
                    
                    all_student_records.append({
                        "subject": subject_name,
                        "batchNo": data['batchNo'],
                        "studentId": student_id,
                        "studentName": data['name'],
                        "from": missing_dates[0] if missing_dates else '',
                        "to": missing_dates[-1] if missing_dates else '',
                        "studentPhNumber": phone_data['studentPhNumber'],
                        "parentNumber": phone_data['parentNumber'],
                        "total_present": recent_present,
                        "total_absent": recent_absent,
                        "missing_streaks": missing_dates
                    })
        
        # Create Excel file with specific column order
        df = pd.DataFrame(all_student_records)
        df = df[['batchNo', 'studentId', 'studentName', 'from', 'to', 'total_absent', 'studentPhNumber', 'parentNumber']]
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Missing_Attendance')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'missing_attendance_{location}.xlsx'
        )