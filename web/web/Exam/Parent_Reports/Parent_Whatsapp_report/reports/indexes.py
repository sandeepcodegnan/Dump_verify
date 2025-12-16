from web.Exam.exam_central_db import db

# Define the indexes to ensure
indexes = {
    'student_login_details': [
        [('id', 1)],  # Used by codeplayground
        [('studentId', 1)],
        [('BatchNo', 1)],
        [('email', 1)],
        [('location', 1)],
        [('BatchNo', 1), ('location', 1)],
    ],
    'Batches': [
        [('Batch', 1)],
        [('location', 1)],
        [('StartDate', 1)],
        [('EndDate', 1)],
    ],
    'Attendance': [
        [('batchNo', 1)],
        [('location', 1)],
        [('datetime', 1)],
        [('course', 1)],
        [('batchNo', 1), ('datetime', 1)],
        [('students.studentId', 1)],
        [('datetime', 1), ('students.studentId', 1)],
    ],
    'Daily-Exam': [
        [('studentId', 1)],
        [('examId', 1)],
        [('startDate', 1)],
        [('examName', 1)],
        [('startDate', 1), ('studentId', 1)],
        [('studentId', 1), ('startDate', 1)],
    ],
    'jobs_listing': [
        [('id', 1)],
        [('jobLocation', 1)],
        [('timestamp', 1)],
        [('applicants_ids', 1)],
        [('selected_students_ids', 1)],
        [('timestamp', 1), ('applicants_ids', 1)],
    ],
    'parent_whatapp_report': [
        [('period_id', 1), ('report_type', 1)],
        [('period_id', 1), ('report_type', 1), ('locations', 1)],
    ],
    'parent_message_status': [
        [('period_id', 1), ('report_type', 1)],
        [('period_id', 1), ('location', 1), ('report_type', 1)],
        [('batches', 1)],
    ],
    'parent_report_status': [
        [('report_type', 1), ('period_id', 1)],
    ],
}


def ensure_indexes():
    for coll_name, specs in indexes.items():
        coll = db[coll_name]
        existing = coll.index_information()
        
        for spec in specs:
            # Check if an index with the same key pattern already exists
            index_exists = False
            for existing_name, existing_info in existing.items():
                if existing_info.get('key') == spec:
                    print(f"Index with same pattern already exists as '{existing_name}' on {coll_name}, skipping")
                    index_exists = True
                    break
            
            if not index_exists:
                name = '_'.join(f"{field}_{direction}" for field, direction in spec)
                try:
                    print(f"Creating index {name} on {coll_name}")
                    coll.create_index(spec, background=True)
                except Exception as e:
                    print(f"Failed to create index {name} on {coll_name}: {e}")


if __name__ == '__main__':
    ensure_indexes()
    print("Index check complete.")
