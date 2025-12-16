"""Code Execution Service - Handles code compilation and test execution"""
from typing import Dict
from web.Exam.Daily_Exam.utils.validation.validation_utils import ValidationUtils
from web.Exam.Daily_Exam.repositories.core.repository_factory import RepositoryFactory
from web.Exam.Daily_Exam.external.onecompiler_client import OneCompilerClient

class CodeExecutionService:
    def __init__(self):
        self.repo_factory = RepositoryFactory()
        self.compiler_client = OneCompilerClient()
    
    def execute_code(self, payload: Dict) -> Dict:
        """Execute code with compiler and test cases"""
        if not payload.get("question_id") or not payload.get("source_code") or not payload.get("language"):
            raise ValueError("Missing required fields: question_id, source_code, language")
        
        ValidationUtils.validate_required_fields(payload, "question_id", "source_code", "language", "subject")
        
        qid = payload["question_id"]
        src_code = payload["source_code"]
        lang = payload["language"]
        subject = payload["subject"].strip().lower()
        
        sample_input = payload.get("sample_input")
        sample_output = payload.get("sample_output", "")
        custom_enabled = payload.get("custom_input_enabled", False)
        custom_input = payload.get("custom_input")
        
        if not all([qid, src_code.strip(), subject]):
            return {"error": "Missing required fields"}
        
        question_repo = self.repo_factory.get_question_repo(subject)
        hidden_cases = question_repo.get_hidden_tests(qid)
        
        return self.compiler_client.execute_code(
            qid, src_code, lang, subject,
            sample_input, sample_output, hidden_cases,
            custom_enabled, custom_input
        )