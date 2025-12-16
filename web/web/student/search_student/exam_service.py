from web.db.db_utils import get_collection, get_db


def get_exam_results_optimized(self, student_data, request):
    """
    Optimized exam results function with complete analysis processing
    """
    # Query parameter support functions
    def get_query_params(*param_names):
        params = {}
        for param in param_names:
            value = request.args.get(param)
            if value:
                params[param] = value
        return params
    
    def validate_exam_type(exam_type):
        valid_types = ["Daily-Exam", "Weekly-Exam", "Monthly-Exam"]
        return exam_type if exam_type in valid_types else "Daily-Exam"
    
    # Get query parameters
    params = get_query_params("batch", "examName")
    exam_name = params.get("examName")
    exam_type = validate_exam_type(request.args.get("examType") or "Daily-Exam")
    
    # Build match conditions
    match_conditions = {"studentId": student_data["id"]}
    if params.get("batch"):
        match_conditions["batch"] = params["batch"]
    if exam_name:
        match_conditions["examName"] = exam_name
    
    # Determine collections to query
    exam_collections = [exam_type] if exam_name or params.get("batch") else ["Daily-Exam", "Weekly-Exam", "Monthly-Exam"]
    aggregated_data = {}

    for coll_name in exam_collections:
        try:
            collection = get_collection(coll_name.lower().replace('-', '_'))
            pipeline = [
                {"$match": match_conditions},
                {"$sort": {"startDate": -1}},
                {
                    "$lookup": {
                        "from": "student_login_details",
                        "localField": "studentId",
                        "foreignField": "id",
                        "as": "student"
                    }
                },
                {"$unwind": "$student"},
                {
                    "$project": {
                        "examName": 1,
                        "totalExamTime": 1,
                        "startDate": 1,
                        "startTime": 1,
                        "paper": 1,
                        "analysis": 1,
                        "subjects": 1,
                        "batch": 1,
                        "location": 1,
                        "examType": {"$literal": coll_name},
                        "student.name": 1,
                        "student.studentId": 1,
                        "student.id": 1,
                        "student.studentPhNumber": 1
                    }
                }
            ]

            for exam in collection.aggregate(pipeline):
                stu_info = exam["student"]
                key = f'{stu_info["id"]}_{exam["examName"]}_{coll_name}'
                
                if key not in aggregated_data:
                    aggregated_data[key] = {
                        "student": {
                            "id": stu_info["id"],
                            "name": stu_info["name"],
                            "studentId": stu_info["studentId"],
                            "phNumber": stu_info.get("studentPhNumber")
                        },
                        "subjects": {},
                        "examDetails": {
                            "examName": exam["examName"],
                            "examType": exam["examType"],
                            "startDate": str(exam.get("startDate")) if exam.get("startDate") else None,
                            "startTime": str(exam.get("startTime")) if exam.get("startTime") else None,
                            "totalExamTime": exam.get("totalExamTime"),
                            "batch": exam.get("batch"),
                            "location": exam.get("location")
                        },
                        "totalMarks": {"mcq": 0, "coding": 0},
                        "obtainedMarks": {"mcq": 0, "coding": 0},
                        "percentage": 0
                    }

                subject_map = {}
                subjects_summary = aggregated_data[key]["subjects"]

                def init_subject(name: str):
                    if name not in subjects_summary:
                        subjects_summary[name] = {
                            "max_mcq_marks": 0,
                            "obtained_mcq_marks": 0,
                            "max_code_marks": 0,
                            "obtained_code_marks": 0,
                            "total_marks": 0,
                            "obtained_marks": 0,
                            "percentage": 0
                        }

                # Process paper subjects
                paper_subjects = exam.get("paper", [])
                if not paper_subjects and exam.get("subjects"):
                    paper_subjects = [
                        {
                            "subject": s.get("subject") or s.get("name") or "Unknown",
                            "MCQs": [],
                            "Coding": []
                        }
                        for s in exam["subjects"]
                    ]

                # Process MCQ and Coding questions
                for sub in paper_subjects:
                    sname = sub.get("subject", "UnknownSubject")
                    init_subject(sname)

                    for mcq in sub.get("MCQs", []):
                        qid = mcq.get("questionId")
                        score = float(mcq.get("Score", 1))
                        subjects_summary[sname]["max_mcq_marks"] += score
                        aggregated_data[key]["totalMarks"]["mcq"] += score
                        subject_map[qid] = {"subject": sname, "type": "mcq"}

                    for code in sub.get("Coding", []):
                        qid = code.get("questionId")
                        score = float(code.get("Score", 1))
                        subjects_summary[sname]["max_code_marks"] += score
                        aggregated_data[key]["totalMarks"]["coding"] += score
                        subject_map[qid] = {"subject": sname, "type": "code"}

                # Process analysis results - COMPLETE IMPLEMENTATION
                analysis_details = exam.get("analysis", {}).get("details", [])
                for row in analysis_details:
                    qid = row.get("questionId")
                    score_awarded = float(row.get("scoreAwarded", 0))
                    meta = subject_map.get(qid)
                    
                    if meta:
                        subj_name = meta["subject"]
                        if meta["type"] == "mcq":
                            subjects_summary[subj_name]["obtained_mcq_marks"] += score_awarded
                            aggregated_data[key]["obtainedMarks"]["mcq"] += score_awarded
                        else:
                            subjects_summary[subj_name]["obtained_code_marks"] += score_awarded
                            aggregated_data[key]["obtainedMarks"]["coding"] += score_awarded

                # Calculate percentages for each subject
                for subject_name, subject_data in subjects_summary.items():
                    total_marks = subject_data["max_mcq_marks"] + subject_data["max_code_marks"]
                    obtained_marks = subject_data["obtained_mcq_marks"] + subject_data["obtained_code_marks"]
                    subject_data["total_marks"] = total_marks
                    subject_data["obtained_marks"] = obtained_marks
                    subject_data["percentage"] = round((obtained_marks / total_marks * 100), 2) if total_marks > 0 else 0

                # Calculate overall percentage
                total_exam_marks = aggregated_data[key]["totalMarks"]["mcq"] + aggregated_data[key]["totalMarks"]["coding"]
                total_obtained_marks = aggregated_data[key]["obtainedMarks"]["mcq"] + aggregated_data[key]["obtainedMarks"]["coding"]
                aggregated_data[key]["percentage"] = round((total_obtained_marks / total_exam_marks * 100), 2) if total_exam_marks > 0 else 0
                
        except Exception as e:
            print(f"Error processing {coll_name}: {e}")
            continue

    return {
        "success": True,
        "studentId": student_data["id"],
        "total_exams": len(aggregated_data),
        "reports": list(aggregated_data.values()),
        "query_params": params if params else None
    }
