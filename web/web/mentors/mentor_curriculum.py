from flask import request, jsonify
from flask_restful import Resource
from web.jwt.auth_middleware import mentor_required
from datetime import datetime
from web.db.db_utils import get_db, get_mcq_collection, get_code_collection, get_query_collection

db = get_db()


def verify_questions_for_tags(subject, subtopics):

    subject_lower = subject.lower()
    mcq_coll = f"{subject_lower}_mcq"
    coll_names = db.list_collection_names()

    # We block if the MCQ collection itself doesn't exist at all:
    if mcq_coll not in coll_names:
        return False, f"Missing required MCQ collection: {mcq_coll}."

    # For SQL subjects, only check MCQ and Query collections
    from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
    is_sql_subject = subject_lower in SQL_SUBJECTS
    
    if is_sql_subject:
        query_coll = f"{subject_lower}_query"
        query_collection_exists = (query_coll in coll_names)
    else:
        code_coll = f"{subject_lower}_code"
        code_collection_exists = (code_coll in coll_names)

    warnings = []
    for sub in subtopics:
        if sub.get("status") != "true":
            continue

        tag = sub.get("tag")
        if not tag:
            continue

        tag_lower = tag.lower()
        exists_mcq = get_mcq_collection(subject).find_one({"Tags": tag_lower})

        missing_types = []
        
        if not exists_mcq:
            missing_types.append("MCQ")

        if is_sql_subject:
            # For SQL subjects, check query questions
            exists_query = None
            if query_collection_exists:
                exists_query = get_query_collection(subject).find_one({"Tags": tag_lower})
            
            if query_collection_exists and not exists_query:
                missing_types.append("Query")
        else:
            # For non-SQL subjects, check code questions
            exists_code = None
            if code_collection_exists:
                exists_code = get_code_collection(subject).find_one({"Tags": tag_lower})
            
            if code_collection_exists and not exists_code:
                missing_types.append("Code")
        
        if missing_types:
            warnings.append(f"{tag}: Missing {', '.join(missing_types)} questions")

    message = "; ".join(warnings) if warnings else ""
    return True, message

class Mentor_CurriCulum(Resource):
    def __init__(self):
        super().__init__()

    @mentor_required
    def get(self):
        mentorId = request.args.get("mentorId")
        subject = request.args.get("subject")
        batch = request.args.get("batch")
        if not mentorId or not subject or not batch:
            return {"error": "Missing required parameters: mentorId, subject, and batch."}, 400

        doc = db.Mentor_Curriculum_Table.find_one(
            {"mentorId": mentorId, "subject": subject, "batch": batch},
            {"curriculumTable": 1, "_id": 0}
        )
        if doc:
            return doc.get("curriculumTable", {}), 200
        else:
            return {"error": "No document found."}, 404

    @staticmethod
    def extract_day(tag):
        """
        Extracts the day number from a tag of the format "Day-<number>:<id>".
        Returns the day as an integer or None if extraction fails.
        """
        try:
            return int(tag.split(":")[0].replace("Day-", ""))
        except Exception:
            return None
    
    def post(self):
        payload = request.get_json()
        mentorId = payload.get("mentorId")
        subject = payload.get("subject")
        batch = payload.get("batch")
        update_data = payload.get("data")

        if not mentorId or not subject or not batch or not update_data:
            return {"error": "Missing required fields: mentorId, subject, batch, and data."}, 400

        # Retrieve the matching mentor curriculum document.
        doc = db.Mentor_Curriculum_Table.find_one({
            "mentorId": mentorId,
            "subject": subject,
            "batch": batch
        })

        if not doc:
            return {"error": "No document found for the given mentorId, subject, and batch."}, 404

        curriculum_table = doc.get("curriculumTable", {})

        accumulated_warnings = []
        # Process each key in the update payload.
        for key, new_value in update_data.items():
            # Get all subtopics from the new value.
            subtopics = new_value.get("SubTopics", [])
            # Validate only the subtopics with status "true".
            valid, msg = verify_questions_for_tags(subject, subtopics)
            if not valid:
                return {"error": msg}, 400
            if msg:
                accumulated_warnings.append(msg)

            timestamp_current = datetime.now().isoformat()

            if key in curriculum_table:
                current_entry = curriculum_table[key]
                # Separate subtopics into completed and incomplete.
                updated_subtopics = []
                false_subtopics = []
                for sub in new_value.get("SubTopics", []):
                    if sub.get("status") == "true":
                        updated_subtopics.append(sub)
                    else:
                        false_subtopics.append(sub)

                # Update the current entry with completed subtopics.
                if updated_subtopics:
                    current_entry.update({
                        "SubTopics": updated_subtopics,
                        "Topics": new_value.get("Topics", current_entry.get("Topics")),
                        "subject": new_value.get("subject", current_entry.get("subject")),
                        "videoUrl": new_value.get("videoUrl", current_entry.get("videoUrl")),
                        "createdAt": timestamp_current
                    })

                # For each incomplete subtopic, determine its target day and move it.
                if false_subtopics:
                    # Determine the tag suffix based on videoUrl.
                    tag_suffix = "_code" if new_value.get("videoUrl") and new_value.get("videoUrl").strip() != "" else "_mcq"
                    for sub in false_subtopics:
                        tag = sub.get("tag", "")
                        current_day = self.extract_day(tag)
                        if current_day is None:
                            continue
                        target_day = current_day + 1

                        # Look for an existing entry in the curriculum_table (other than the current key)
                        # that already belongs to the target day.
                        existing_key = None
                        for k, entry in curriculum_table.items():
                            if k == key:
                                continue
                            sub_list = entry.get("SubTopics", [])
                            if sub_list and any(st.get("tag", "").startswith(f"Day-{target_day}:") for st in sub_list):
                                existing_key = k
                                break

                        if existing_key:
                            # Append the subtopic to the existing target day entry.
                            curriculum_table[existing_key]["SubTopics"].append(sub)
                            curriculum_table[existing_key]["createdAt"] = datetime.now().isoformat()
                        else:
                            # Create a new entry for the target day.
                            new_key = f"{key}_Day{target_day}{tag_suffix}"
                            if new_key in curriculum_table:
                                curriculum_table[new_key]["SubTopics"].append(sub)
                                curriculum_table[new_key]["createdAt"] = datetime.now().isoformat()
                            else:
                                curriculum_table[new_key] = {
                                    "subject": new_value.get("subject", current_entry.get("subject")),
                                    "Topics": new_value.get("Topics", current_entry.get("Topics")),
                                    "videoUrl": new_value.get("videoUrl", current_entry.get("videoUrl")),
                                    "SubTopics": [sub],
                                    "createdAt": datetime.now().isoformat()
                                }
            else:
                new_value["createdAt"] = datetime.now().isoformat()
                curriculum_table[key] = new_value

        result = db.Mentor_Curriculum_Table.update_one(
            {"_id": doc["_id"]},
            {"$set": {"curriculumTable": curriculum_table}}
        )

        final_warning_message = "; ".join(accumulated_warnings)

        if result.modified_count > 0:
            return {"message": "Mentor curriculum table updated successfully.", "warning": final_warning_message}, 200
        else:
            return {"message": "No changes made."}, 200