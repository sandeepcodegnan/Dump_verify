from web.db.db_utils import get_collection

def Attendance_service(self,std_id):
     # Attendance Records - Use aggregation to get ALL data
        attendance_pipeline = [
            {"$match": {"students.studentId": std_id}},
            {"$unwind": "$students"},
            {"$match": {"students.studentId": std_id}},
            {"$sort": {"datetime": -1}},
            {"$project": {
                "studentId": "$students.studentId",
                "course": 1,
                "subject": 1,
                "topic": 1,
                "batchNo": 1,
                "name": "$students.name",
                "status": "$students.status",
                "remarks": "$students.remarks",
                "datetime": 1,
                "location": 1,
                "trainer": 1,
                "session": 1
            }}
        ]
        Attends_data = list(get_collection('attendance').aggregate(attendance_pipeline))
        for attend in Attends_data:
            attend["_id"] = str(attend["_id"])
            attend["datetime"] = str(attend.get('datetime')) if attend.get('datetime') else None
        
        return  Attends_data