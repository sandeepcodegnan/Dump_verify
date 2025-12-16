from web.Exam.exam_central_db import db


def fetch_batch_report_docs(batch_name: str, location: str, start_str: str, end_str: str):
    """
    Returns a list of dicts, one per student in the batch, with all
    attendance, exam & placement data (both total and period‑specific) populated.
    Dates must be ISO strings: YYYY‑MM‑DD.
    """
    pipeline = [
        # 1) Filter to this batch + location + exclude placed students
        {"$match": {
            "BatchNo": batch_name, 
            "location": location,
            "$or": [
                {"placed": {"$ne": True}},
                {"placed": {"$exists": False}}
            ]
        }},

        # 2) Attendance lookup & format as subject-date structure
        {"$lookup": {
            "from": "Attendance",
            "let": {"sid": "$studentId"},
            "pipeline": [
                {"$unwind": "$students"},
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$students.studentId", "$$sid"]},
                    {"$gte": ["$datetime", start_str]},
                    {"$lte": ["$datetime", end_str]}
                ]}}},
                {"$group": {
                    "_id": "$course",
                    "dates": {"$push": {"date": "$datetime", "status": "$students.status"}}
                }},
                {"$project": {
                    "subject": "$_id",
                    "attendance": {"$arrayToObject": {"$map": {
                        "input": "$dates",
                        "as": "d",
                        "in": {"k": "$$d.date", "v": "$$d.status"}
                    }}},
                    "percentage": {"$multiply": [
                        {"$divide": [
                            {"$size": {"$filter": {"input": "$dates", "cond": {"$eq": ["$$this.status", "present"]}}}},
                            {"$size": "$dates"}
                        ]}, 100
                    ]}
                }}
            ],
            "as": "attendanceList"
        }},
        
        # 2.1) Practice Attendance lookup & format as course-date structure
        {"$lookup": {
            "from": "Practice_Attendance",
            "let": {"sid": "$studentId"},
            "pipeline": [
                {"$unwind": "$students"},
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$students.studentId", "$$sid"]},
                    {"$gte": ["$datetime", start_str]},
                    {"$lte": ["$datetime", end_str]}
                ]}}},
                {"$group": {
                    "_id": "$course",
                    "dates": {"$push": {"date": "$datetime", "status": "$students.status"}}
                }},
                {"$project": {
                    "course": "$_id",
                    "attendance": {"$arrayToObject": {"$map": {
                        "input": "$dates",
                        "as": "d",
                        "in": {"k": "$$d.date", "v": "$$d.status"}
                    }}},
                    "percentage": {"$multiply": [
                        {"$divide": [
                            {"$size": {"$filter": {"input": "$dates", "cond": {"$eq": ["$$this.status", "present"]}}}},
                            {"$size": "$dates"}
                        ]}, 100
                    ]}
                }}
            ],
            "as": "practiceAttendanceList"
        }},
        {"$addFields": {
            "attendance": {"$arrayToObject": {"$map": {
                "input": "$attendanceList",
                "as": "subj",
                "in": {
                    "k": {"$ifNull": ["$$subj.subject", "General"]},
                    "v": {"$mergeObjects": [
                        "$$subj.attendance",
                        {"percentage": {"$round": ["$$subj.percentage", 0]}}
                    ]}
                }
            }}}
        }},
        {"$addFields": {
            "attendance": {"$cond": [
                {"$gt": [{"$size": "$attendanceList"}, 0]},
                {"$mergeObjects": [
                    "$attendance",
                    {"overallPercentage": {"$round": [{"$avg": {"$map": {
                        "input": "$attendanceList",
                        "as": "subj",
                        "in": "$$subj.percentage"
                    }}}, 0]}}
                ]},
                "$attendance"
            ]}
        }},
        {"$addFields": {
            "practiceAttendance": {"$arrayToObject": {"$map": {
                "input": "$practiceAttendanceList",
                "as": "course",
                "in": {
                    "k": {"$ifNull": ["$$course.course", "General"]},
                    "v": {"$mergeObjects": [
                        "$$course.attendance",
                        {"percentage": {"$round": ["$$course.percentage", 0]}}
                    ]}
                }
            }}}
        }},
        {"$addFields": {
            "practiceAttendance": {"$cond": [
                {"$gt": [{"$size": "$practiceAttendanceList"}, 0]},
                {"$mergeObjects": [
                    "$practiceAttendance",
                    {"overallPercentage": {"$round": [{"$avg": {"$map": {
                        "input": "$practiceAttendanceList",
                        "as": "course",
                        "in": "$$course.percentage"
                    }}}, 0]}}
                ]},
                "$practiceAttendance"
            ]}
        }},

        # 3) Exams lookup + compute subject‑wise and totals safely
        {"$lookup": {
            "from": "Daily-Exam",
            "let": {"uid": "$id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$studentId", "$$uid"]},
                    {"$gte": ["$startDate", start_str]},
                    {"$lte": ["$startDate", end_str]},
                    {"$ne": ["$examName", None]}
                ]}}},
                {"$group": {
                    "_id": {"exam": "$examName"},
                    "paper":    {"$first": "$paper"},
                    "analysis": {"$first": "$analysis"}
                }},
                {"$addFields": {
                    "subjects": {"$map": {
                        "input": {"$ifNull": ["$paper", []]},
                        "as": "sec",
                        "in": {
                            "subject": "$$sec.subject",
                            "maxScore": {"$add": [
                                {"$sum": {"$map": {
                                    "input": {"$ifNull": ["$$sec.MCQs", []]},
                                    "as": "m",
                                    "in": {"$convert": {"input": {"$ifNull": ["$$m.Score", 0]}, "to": "int", "onError": 0}}
                                }}},
                                {"$sum": {"$map": {
                                    "input": {"$ifNull": ["$$sec.Coding", []]},
                                    "as": "c",
                                    "in": {"$convert": {"input": {"$ifNull": ["$$c.Score", 0]}, "to": "int", "onError": 0}}
                                }}}
                            ]},
                            "score": {"$cond": [
                                {"$and": [
                                    {"$ne": ["$analysis", None]},
                                    {"$ne": ["$analysis.subjectBreakdown", None]},
                                    {"$ne": [{"$getField": {
                                        "field": "$$sec.subject",
                                        "input": {"$ifNull": ["$analysis.subjectBreakdown", {}]}
                                    }}, None]}
                                ]},
                                {"$convert": {
                                    "input": {"$getField": {
                                        "field": "score",
                                        "input": {"$getField": {
                                            "field": "$$sec.subject",
                                            "input": {"$ifNull": ["$analysis.subjectBreakdown", {}]}
                                        }}
                                    }},
                                    "to": "int",
                                    "onError": 0
                                }},
                                0
                            ]}
                        }
                    }}
                }},
                {"$addFields": {
                    "totalMarks": {
                        "score": {"$sum": "$subjects.score"},
                        "maxScore": {"$sum": "$subjects.maxScore"}
                    }
                }},
                {"$addFields": {
                    "percentage": {"$cond": [
                        {"$gt": ["$totalMarks.maxScore", 0]},
                        {"$floor": {"$multiply": [
                            {"$divide": ["$totalMarks.score", "$totalMarks.maxScore"]},
                            100
                        ]}},
                        0
                    ]}
                }},
                {"$project": {
                    "_id":        0,
                    "examName":   "$_id.exam",
                    "subjects":   1,
                    "totalMarks": 1,
                    "percentage": 1,
                    "status": {"$cond": [{"$gt": ["$totalMarks.score", 0]}, "attempted", "not_attempted"]}
                }}
            ],
            "as": "dailyExam"
        }},

        # 4) Placement lookup & counts (overall + period) with threshold logic
        {"$lookup": {
            "from": "Batches",
            "localField": "BatchNo",
            "foreignField": "Batch",
            "as": "batchInfo"
        }},
        {"$lookup": {
            "from": "jobs_listing",
            "let": {
                "sid": "$id",
                "skills": {"$ifNull": ["$studentSkills", []]},
                "pct": "$highestGraduationpercentage",
                "year": {"$toString": "$yearOfPassing"},
                "dept": {"$toLower": {"$ifNull": ["$department", ""]}},
                "placement_status": {"$ifNull": ["$placementStatus", True]},
                "placed_status": {"$ifNull": ["$placed", False]},
                "batch_no": {"$ifNull": ["$BatchNo", ""]},
                "batch_start": {"$ifNull": [{"$arrayElemAt": ["$batchInfo.StartDate", 0]}, None]}
            },
            "pipeline": [
                {"$addFields": {
                    "jobDate": {"$dateFromString": {"dateString": "$timestamp", "onError": None}},
                    "batchStartDate": {"$dateFromString": {"dateString": "$$batch_start", "onError": None}},
                    "thresholdDate": {"$dateFromString": {"dateString": "2025-07-12"}}
                }},
                {"$match": {
                    "$expr": {"$or": [
                        {"$eq": ["$$batch_start", None]},
                        {"$gte": ["$jobDate", "$batchStartDate"]}
                    ]}
                }},
                {"$addFields": {
                    "skillsMatch": {"$gt": [{"$size": {"$setIntersection": [{"$ifNull": ["$jobSkills", []]}, "$$skills"]}}, 0]},
                    "beforeThreshold": {"$lte": ["$jobDate", "$thresholdDate"]},
                    "percentageOk": {"$gte": ["$$pct", {"$toDouble": {"$ifNull": ["$percentage", 0]}}]},
                    "yearOk": {"$in": ["$$year", {"$map": {"input": {"$ifNull": ["$graduates", []]}, "as": "g", "in": {"$toString": "$$g"}}}]},
                    "deptOk": {"$or": [
                        {"$in": ["any branch", {"$map": {"input": {"$ifNull": ["$department", []]}, "as": "d", "in": {"$toLower": "$$d"}}}]},
                        {"$in": ["$$dept", {"$map": {"input": {"$ifNull": ["$department", []]}, "as": "d", "in": {"$toLower": "$$d"}}}]}
                    ]}
                }},
                {"$addFields": {
                    "isEligible": {"$and": [
                        {"$ne": ["$$placement_status", False]},
                        {"$not": [{"$regexMatch": {"input": "$$batch_no", "regex": "^DROPOUTS-"}}]},
                        "$skillsMatch",
                        {"$or": [
                            "$beforeThreshold",
                            {"$and": ["$percentageOk", "$yearOk", "$deptOk"]}
                        ]}
                    ]}
                }},
                {"$group": {
                    "_id": None,
                    "totalJobs": {"$sum": 1},
                    "totalEligible": {"$sum": {"$cond": ["$isEligible", 1, 0]}},
                    "totalApplied": {"$sum": {"$cond": [{"$in": ["$$sid", {"$ifNull": ["$applicants_ids", []]}]}, 1, 0]}},
                    "periodJobs": {"$sum": {"$cond": [{"$and": [{"$gte": ["$timestamp", start_str]}, {"$lte": ["$timestamp", end_str]}]}, 1, 0]}},
                    "periodEligible": {"$sum": {"$cond": [{"$and": [{"$gte": ["$timestamp", start_str]}, {"$lte": ["$timestamp", end_str]}, "$isEligible"]}, 1, 0]}},
                    "periodApplied": {"$sum": {"$cond": [{"$and": [{"$gte": ["$timestamp", start_str]}, {"$lte": ["$timestamp", end_str]}, {"$in": ["$$sid", {"$ifNull": ["$applicants_ids", []]}]}]}, 1, 0]}}
                }}
            ],
            "as": "placementStats"
        }},
        {"$addFields": {
            "placement": {"$arrayElemAt": ["$placementStats", 0]}
        }},
        {"$project": {
            "batchInfo": 0
        }},

        # Format exam data
        {"$addFields": {
            "formattedExams": {"$arrayToObject": {"$map": {
                "input": "$dailyExam",
                "as": "exam",
                "in": {
                    "k": {"$ifNull": ["$$exam.examName", "General-Exam"]},
                    "v": {"$mergeObjects": [
                        {"$arrayToObject": {"$map": {"input": {"$ifNull": ["$$exam.subjects", []]}, "as": "subj", "in": {"k": {"$ifNull": ["$$subj.subject", "Unknown"]}, "v": {"score": {"$ifNull": ["$$subj.score", 0]}, "maxScore": {"$ifNull": ["$$subj.maxScore", 0]}}}}}},
                        {"totalMarks": {"$ifNull": ["$$exam.totalMarks", {"score": 0, "maxScore": 0}]}, "percentage": {"$ifNull": ["$$exam.percentage", 0]}, "status": {"$ifNull": ["$$exam.status", "not_attempted"]}}
                    ]}
                }
            }}}
        }},

        
        # 7) Project final shape
        {"$project": {
            "_id":           0,
            "id":            1,
            "name":          1,
            'location':     1,
            "studentPhone":  "$studentPhNumber",
            "parentPhone":   "$parentNumber",
            "attendance":    {"$ifNull": ["$attendance", {}]},
            "practiceAttendance": {"$ifNull": ["$practiceAttendance", {}]},
            "dailyExam":     "$formattedExams",
            "placement": {"$cond": [
                {"$ne": ["$placementStatus", False]},
                {
                    "total_jobs": {"$ifNull": ["$placement.totalJobs", 0]},
                    "eligible_jobs": {"$ifNull": ["$placement.totalEligible", 0]},
                    "applied_jobs": {"$ifNull": ["$placement.totalApplied", 0]},
                    "period_jobs": {"$ifNull": ["$placement.periodJobs", 0]},
                    "period_eligible": {"$ifNull": ["$placement.periodEligible", 0]},
                    "period_applied": {"$ifNull": ["$placement.periodApplied", 0]}
                },
                {}
            ]
        }}}
    ]

    # Get raw results from MongoDB
    results = list(db["student_login_details"].aggregate(pipeline, allowDiskUse=True))
    
    # Reorder fields to ensure consistent output format
    ordered_results = []
    for doc in results:
        ordered_doc = {
            "id": doc.get("id"),
            "name": doc.get("name"),
            "location": doc.get("location"),
            "studentPhone": doc.get("studentPhone"),
            "parentPhone": doc.get("parentPhone"),
            "attendance": doc.get("attendance", []),
            "practiceAttendance": doc.get("practiceAttendance", {}),
            "dailyExam": doc.get("dailyExam", {}),
            "placement": doc.get("placement", {})
        }
        ordered_results.append(ordered_doc)
    
    return ordered_results