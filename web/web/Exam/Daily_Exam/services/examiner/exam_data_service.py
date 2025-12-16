"""Exam Data Service - Fetch curriculum data for exam generation"""
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS, EXCLUDED_EXAM_SUBJECTS
from web.Exam.Daily_Exam.utils.time.timeutils import parse_date_safe
from web.Exam.Daily_Exam.utils.time.week_utils import get_week_range, get_month_range
from web.Exam.Daily_Exam.utils.processing.parallel_processor import ParallelProcessor
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.utils.cache.cache_utils import exam_cache
from hashlib import sha256

class ExamDataService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
        self.cache = exam_cache
    
    def get_curriculum_data(self, date, batch, location, exam_type="Daily-Exam", subjects=None):
        # Create cache key
        cache_key = sha256(f"{date}_{batch}_{location}_{exam_type}_{subjects}".encode()).hexdigest()
        
        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            cached_result["cached"] = True
            return cached_result
        
        exam_type = ExamValidationService.validate_exam_type(exam_type)
        parse_date_safe(date)
        
        # Safety check - prevent duplicate exam creation
        if exam_type in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(exam_type)
        else:
            exam_repo = self.repo_factory.get_exam_repo(exam_type)
        
        if exam_repo.exists_for_date(batch, location, date):
            raise ValueError(f"Exam already exists for batch {batch} on {date}. Cannot generate duplicate exam.")
        
        curriculum_repo = self.repo_factory.get_curriculum_repo()
        
        date_range = None
        if exam_type == "Weekly-Exam":
            start_date, end_date = get_week_range(date)
            date_range = {"startDate": start_date, "endDate": end_date}
            subj_docs = curriculum_repo.get_curriculum_data_range(start_date, end_date, batch, location)
        elif exam_type == "Monthly-Exam":
            start_date, end_date = get_month_range(date)
            date_range = {"startDate": start_date, "endDate": end_date}
            subj_docs = curriculum_repo.get_curriculum_data_range(start_date, end_date, batch, location)
        else:
            subj_docs = curriculum_repo.get_curriculum_data(date, batch, location)
        
        if not subj_docs:
            raise ValueError("Sorry - Nothing has been scheduled for Today.")
        
        # Filter out excluded subjects
        subj_docs = [doc for doc in subj_docs if doc["subject"].lower() not in EXCLUDED_EXAM_SUBJECTS]
        
        # Filter by subjects if provided
        if subjects:
            subject_list = [s.strip() for s in subjects.split(",")]
            subj_docs = [doc for doc in subj_docs if doc["subject"] in subject_list]
        
        results = ParallelProcessor.process_with_timeout(
            subj_docs, lambda sd: self._process_subject(sd, date, curriculum_repo), timeout=10, task_type="subject"
        )
        
        data, missing_mcq, warnings = {}, [], []
        for result in results:
            if result["type"] == "success":
                data[result["subject"]] = result["data"]
                warnings.extend(result["warnings"])
            elif result["type"] == "missing":
                missing_mcq.append(result["subject"])
        
        if not data:
            raise ValueError(f"We couldn't find any MCQ questions for these subjects: {', '.join(missing_mcq)}. Please let the admin know." if missing_mcq else "We couldn't find any MCQ questions for the selected subjects. Please let the admin know.")
        
        resp = {"success": True, "data": data}
        if date_range:
            resp["weekRange" if exam_type == "Weekly-Exam" else "monthRange"] = date_range
        if warnings:
            resp["warning"] = "; ".join(warnings)
        if missing_mcq:
            resp["subjects_without_mcq"] = missing_mcq
        
        result = sanitize_mongo_document(resp)
        result["cached"] = False
        
        # Cache result
        self.cache.put(cache_key, result)
        
        return result
    
    def _process_subject(self, sd, date, curriculum_repo):
        try:
            subj = sd["subject"]
            
            # Skip MCQ check for excluded subjects
            if subj.lower() in EXCLUDED_EXAM_SUBJECTS:
                return {
                    "type": "success",
                    "subject": subj,
                    "data": {
                        "date": date,
                        "topics": ", ".join(sd["topics"]),
                        "subtitles": sd["subtitles"],
                        "tags": sd["tags"],
                        "breakdown": {"mcq": {}, "code": {}}
                    },
                    "warnings": []
                }
            
            tags = [t.lower() for t in sd["tags"]]
            is_sql_subject = subj.lower() in SQL_SUBJECTS
            
            mcq_col = f"{subj.lower()}_mcq"
            mcq_break = curriculum_repo.count_by_difficulty(mcq_col, tags)
            
            if sum(mcq_break.values()) == 0:
                return {"type": "missing", "subject": subj}
            
            breakdown_key = "query" if is_sql_subject else "code"
            second_col = f"{subj.lower()}_{breakdown_key}"
            second_break = curriculum_repo.count_by_difficulty(second_col, tags)
            
            tag_warnings = self._validate_tags(subj, tags, mcq_break, second_break, is_sql_subject)
            
            return {
                "type": "success",
                "subject": subj,
                "data": {
                    "date": date,
                    "topics": ", ".join(sd["topics"]),
                    "subtitles": sd["subtitles"],
                    "tags": sd["tags"],
                    "breakdown": {"mcq": mcq_break, breakdown_key: second_break}
                },
                "warnings": tag_warnings
            }
        except Exception as e:
            return {"type": "error", "subject": sd.get("subject", "unknown"), "error": str(e)}
    
    def _validate_tags(self, subject, tags, mcq_count, second_count, is_sql):
        warnings = []
        has_mcq = sum(mcq_count.values()) > 0
        has_second = sum(second_count.values()) > 0
        
        for tag in tags:
            missing = []
            if not has_mcq:
                missing.append("MCQ")
            if not has_second:
                missing.append("Query" if is_sql else "Code")
            if missing:
                warnings.append(f"{tag}: Missing {', '.join(missing)} questions")
        return warnings
