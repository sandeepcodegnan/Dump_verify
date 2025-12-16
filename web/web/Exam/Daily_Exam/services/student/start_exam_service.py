"""Start Exam Service - Handle exam initialization and paper generation"""
import os
from typing import Dict, List
from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
from web.Exam.Daily_Exam.utils.formatting.json_utils import sanitize_mongo_document
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.services.business_logic_validation.exam_validation_service import ExamValidationService
from web.Exam.Daily_Exam.utils.formatting.formatters import sanitize_exam_fields
from web.Exam.Daily_Exam.exceptions.exceptions import ExamAlreadyStartedError
from web.Exam.Daily_Exam.utils.processing.parallel_processor import ParallelProcessor
from web.Exam.Daily_Exam.utils.time.window_utils import WindowStatusChecker

class StartExamService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
    
    def start_exam(self, exam_id: str, collection_name: str) -> Dict:
        """Resilient start exam - handles network issues and paper generation failures"""
        if not exam_id:
            raise ValueError("'examId' is required.")
        if not collection_name:
            raise ValueError("'collectionName' is required.")
        
        if collection_name in {"Weekly-Exam", "Monthly-Exam"}:
            exam_repo = self.repo_factory.get_optimized_exam_repo(collection_name)
            exam = exam_repo.find_student_exam_by_id(exam_id)
        else:
            exam_repo = self.repo_factory.get_exam_repo(collection_name)
            exam = exam_repo.find_by_id(exam_id)
        
        if not exam:
            raise ValueError("Exam not found")
        
        if exam.get("attempt-status") is True:
            raise ValueError("Exam already completed. You cannot start it again.")
        
        # Window Period Enforcement
        if "windowStartTime" in exam and "windowEndTime" in exam:
            window_status = WindowStatusChecker.check_window_status(exam, include_date_check=True)
            if not window_status["canStart"]:
                raise ValueError(window_status["message"])
        
        # Resilient flow: Check if already started with paper
        if exam.get("start-status"):
            if exam.get("paper"):
                return sanitize_mongo_document({
                    "exam": {
                        **exam,
                        "paper": self._sanitize_paper(exam["paper"]),
                        "start-status": True
                    },
                    "success": True
                })
            else:
                # Started but no paper - reset status and continue
                if collection_name in {"Weekly-Exam", "Monthly-Exam"}:
                    exam_repo.collection.update_one(
                        {"students.examId": exam_id},
                        {"$unset": {"students.$.start-status": 1}}
                    )
                    exam = exam_repo.find_student_exam_by_id(exam_id)
                else:
                    exam_repo.collection.update_one(
                        {"examId": exam_id},
                        {"$unset": {"start-status": 1}}
                    )
                    exam = exam_repo.find_by_id(exam_id)
        
        ExamValidationService.validate_exam_timing(exam)
        
        timeout_seconds = int(os.getenv('EXAM_PAPER_BUILD_TIMEOUT', 20))
        
        try:
            paper = self._build_exam_paper_resilient(exam.get("subjects", []), timeout_seconds)
            if not paper:
                raise ValueError("Unable to generate exam paper. Please try again.")
        except ValueError as e:
            if "taking too long" in str(e).lower():
                raise ValueError("Exam preparation is taking too long. Please try again in a moment.")
            raise e
        except Exception as e:
            print(f"Paper building error: {str(e)}")
            raise ValueError("Unable to prepare exam questions. Please contact support if this continues.")
        
        # Atomic update
        if collection_name in {"Weekly-Exam", "Monthly-Exam"}:
            success = exam_repo.update_student_paper_and_status(exam_id, paper)
        else:
            success = exam_repo.update_paper_and_status(exam_id, paper)
        
        if not success:
            raise ExamAlreadyStartedError("It looks like someone already started this exam. Please check with your mentor.")
        
        return sanitize_mongo_document({
            "exam": {
                **exam,
                "paper": self._sanitize_paper(paper),
                "start-status": True
            },
            "success": True
        })
    
    def _build_exam_paper_resilient(self, subjects: List[Dict], timeout: int = 20) -> List[Dict]:
        """Build exam paper with parallel processing and resilience"""
        paper = ParallelProcessor.process_with_timeout(
            tasks=subjects,
            processor_func=self._build_subject_paper,
            timeout=timeout,
            task_type="subject"
        )
        
        if not paper:
            raise ValueError("No questions could be loaded for any subject. Please contact support.")
        
        return paper
    
    def _build_subject_paper(self, subj: Dict) -> Dict:
        """Build paper for single subject with parallel question fetching"""
        name = subj.get("subject", "").strip()
        tags = [t.lower() for t in subj.get("tags", [])]
        
        if not name:
            return None
        
        question_repo = self.repo_factory.get_question_repo(name)
        is_sql_subject = name.lower() in SQL_SUBJECTS
        
        fetch_requests = self._prepare_fetch_requests(subj, tags, is_sql_subject)
        
        if not fetch_requests:
            return None
        
        def fetch_questions(request):
            return question_repo.fetch_questions_batch(
                request["config"], request["second_config"]
            )
        
        mcqs, second_questions = ParallelProcessor.process_requests_parallel(
            requests=fetch_requests,
            processor_func=fetch_questions,
            timeout=15
        )
        
        if is_sql_subject:
            return {
                "subject": name,
                "MCQs": mcqs,
                "Query": second_questions,
                "totalTime": subj.get("totalTime")
            }
        else:
            return {
                "subject": name,
                "MCQs": mcqs,
                "Coding": second_questions,
                "totalTime": subj.get("totalTime")
            }
    
    def _prepare_fetch_requests(self, subj: Dict, tags: List[str], is_sql_subject: bool) -> List[Dict]:
        """Prepare question fetch requests for parallel processing"""
        fetch_requests = []
        
        # MCQ requests
        for diff, amt in subj.get("selectedMCQs", {}).items():
            amount = int(amt) if amt else 0
            if amount > 0:
                fetch_requests.append({
                    "type": "mcq",
                    "config": {"tags": tags, "difficulty": diff, "amount": amount},
                    "second_config": {"amount": 0}
                })
        
        # Second type requests (Query/Coding)
        second_type = "selectedQuery" if is_sql_subject else "selectedCoding"
        for diff, amt in subj.get(second_type, {}).items():
            amount = int(amt) if amt else 0
            if amount > 0:
                fetch_requests.append({
                    "type": "query" if is_sql_subject else "code",
                    "config": {"amount": 0},
                    "second_config": {"tags": tags, "difficulty": diff, "amount": amount}
                })
        
        return fetch_requests
    
    def _sanitize_paper(self, paper: List[Dict]) -> List[Dict]:
        """Remove sensitive fields from questions"""
        sanitized = []
        for subject_paper in paper:
            sanitized_subject = {
                "subject": subject_paper.get("subject"),
                "totalTime": subject_paper.get("totalTime"),
                "MCQs": [sanitize_exam_fields(mcq, "MCQ") for mcq in subject_paper.get("MCQs", [])]
            }
            
            if "Query" in subject_paper:
                sanitized_subject["Query"] = [sanitize_exam_fields(query, "Query") for query in subject_paper.get("Query", [])]
            else:
                sanitized_subject["Coding"] = [sanitize_exam_fields(coding, "Coding") for coding in subject_paper.get("Coding", [])]
            
            sanitized.append(sanitized_subject)
        return sanitized