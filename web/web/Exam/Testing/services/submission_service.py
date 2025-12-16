"""
Submission Service
Business logic for code/SQL submission evaluation
"""
from typing import Dict, List
from web.Exam.Testing.services.base_service import BaseService
from web.Exam.Testing.services.execution_service import ExecutionService
from web.Exam.Testing.services.verification_service import VerificationService
from web.Exam.Testing.utils.formatters import normalize_text, format_test_result
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import QuestionNotFoundError, ExecutionError

class SubmissionService(BaseService):
    """Service for submission evaluation"""
    
    def __init__(self):
        super().__init__()
        self.execution_service = ExecutionService()
        self.verification_service = VerificationService()
    
    def process_submission(self, data: Dict) -> Dict:
        """Process code/SQL submission"""
        InputValidator.validate_question_data(data)
        
        intern_id = data["internId"]
        question_id = data["question_id"]
        source_code = data.get("source_code", "")
        language = data["language"]
        problem_type = data["type"].strip().lower()
        
        # Get question
        question = self._get_question(question_id, problem_type)
        if not question:
            raise QuestionNotFoundError()
        
        # Handle different submission types
        if problem_type in ["query_test", "query_codeplayground_test"]:
            query = data.get("query", "")
            if not query:
                raise ExecutionError("Query field is required for SQL submissions")
            return self._process_sql_submission(data, question, intern_id, query, problem_type)
        else:
            return self._process_code_submission(data, question, intern_id, source_code, language, problem_type)
    
    def _process_code_submission(self, data: Dict, question: Dict, intern_id: str, 
                               source_code: str, language: str, problem_type: str) -> Dict:
        """Process code submission"""
        results = []
        
        # Handle custom input
        custom_input = data.get("custom_input")
        if custom_input is not None:
            if isinstance(custom_input, str) and not custom_input.strip():
                custom_input = None
            
            if custom_input is not None:
                result = self.execution_service.execute_code(source_code, language, custom_input)
                actual = normalize_text(result.get("stdout", ""))
                results.append(format_test_result(custom_input, "", actual, "Passed", "custom"))
                
                return {
                    "message": "Custom input executed",
                    "results": results,
                    "verified": False
                }
        
        # Process test cases
        payload_tests = data.get("hidden_test_cases")
        if payload_tests:
            results = self._process_payload_tests(payload_tests, source_code, language)
        else:
            results = self._process_db_tests(question, source_code, language)
        
        # Check auto-verification
        verified = self._check_auto_verification(results, question, problem_type)
        
        if verified:
            self._auto_verify_submission(intern_id, question, source_code, problem_type)
        
        return {
            "message": "Submission processed",
            "results": results,
            "verified": verified
        }
    
    def _process_sql_submission(self, data: Dict, question: Dict, intern_id: str, query: str, problem_type: str = "query_test") -> Dict:
        """Process SQL submission"""
        sql_content = question.get("Input", "")
        expected_output = normalize_text(question.get("Expected_Output", ""))
        
        if not sql_content:
            raise ExecutionError("SQL question missing table definitions")
        
        # Execute SQL
        result = self.execution_service.execute_sql(query, sql_content)
        
        if result.get("stderr"):
            return {
                "message": "SQL execution failed",
                "results": [format_test_result(query, "", result["stderr"], "Failed", "sql")],
                "verified": False
            }
        
        actual_output = result.get("stdout", "")
        passed = actual_output == expected_output
        
        if passed:
            self._auto_verify_sql_submission(intern_id, question, query, problem_type)
        
        return {
            "message": "SQL query executed",
            "results": [format_test_result(query, expected_output, actual_output, 
                                         "Passed" if passed else "Failed", "sql")],
            "verified": passed
        }
    
    def _process_payload_tests(self, payload_tests: List[Dict], source_code: str, language: str) -> List[Dict]:
        """Process explicit test cases from payload"""
        results = []
        sample_case = next((tc for tc in payload_tests if tc.get("type") == "sample"), None)
        hidden_cases = [tc for tc in payload_tests if tc.get("type") != "sample"]
        
        proceed = True
        
        # Process sample case
        if sample_case:
            expected = normalize_text(sample_case.get("Output", ""))
            exec_result = self.execution_service.execute_code(source_code, language, sample_case["Input"])
            actual = normalize_text(exec_result.get("stdout") or exec_result.get("stderr", ""))
            passed = actual == expected
            
            results.append(format_test_result(sample_case["Input"], expected, actual,
                                            "Passed" if passed else "Failed", "sample"))
            proceed = passed
        
        # Process hidden cases
        if proceed:
            for tc in hidden_cases:
                expected = normalize_text(tc.get("Output", ""))
                exec_result = self.execution_service.execute_code(source_code, language, tc["Input"])
                actual = normalize_text(exec_result.get("stdout") or exec_result.get("stderr", ""))
                passed = actual == expected
                
                results.append(format_test_result(tc["Input"], expected, actual,
                                                "Passed" if passed else "Failed", "hidden"))
                if not passed:
                    # Mark remaining as skipped
                    remaining_idx = hidden_cases.index(tc) + 1
                    for remaining_tc in hidden_cases[remaining_idx:]:
                        exp = normalize_text(remaining_tc.get("Output", ""))
                        results.append(format_test_result(remaining_tc["Input"], exp, "", "Skipped", "hidden"))
                    break
        else:
            # Mark all hidden as skipped
            for tc in hidden_cases:
                exp = normalize_text(tc.get("Output", ""))
                results.append(format_test_result(tc["Input"], exp, "", "Skipped", "hidden"))
        
        return results
    
    def _process_db_tests(self, question: Dict, source_code: str, language: str) -> List[Dict]:
        """Process test cases from database"""
        results = []
        sample_input = question.get("Sample_Input")
        sample_output = normalize_text(question.get("Sample_Output", ""))
        
        proceed = True
        
        # Process sample test
        if sample_input is not None:
            exec_result = self.execution_service.execute_code(source_code, language, sample_input)
            actual = normalize_text(exec_result.get("stdout") or exec_result.get("stderr", ""))
            passed = actual == sample_output
            
            results.append(format_test_result(sample_input, sample_output, actual,
                                            "Passed" if passed else "Failed", "sample"))
            proceed = passed
        
        # Process hidden tests
        hidden_tests = question.get("Hidden_Test_Cases", [])
        if proceed:
            for tc in hidden_tests:
                expected = normalize_text(tc.get("Output", ""))
                exec_result = self.execution_service.execute_code(source_code, language, tc["Input"])
                actual = normalize_text(exec_result.get("stdout") or exec_result.get("stderr", ""))
                passed = actual == expected
                
                results.append(format_test_result(tc["Input"], expected, actual,
                                                "Passed" if passed else "Failed", "hidden"))
                if not passed:
                    # Mark remaining as skipped
                    remaining_idx = hidden_tests.index(tc) + 1
                    for remaining_tc in hidden_tests[remaining_idx:]:
                        exp = normalize_text(remaining_tc.get("Output", ""))
                        results.append(format_test_result(remaining_tc["Input"], exp, "", "Skipped", "hidden"))
                    break
        else:
            # Mark all hidden as skipped
            for tc in hidden_tests:
                exp = normalize_text(tc.get("Output", ""))
                results.append(format_test_result(tc["Input"], exp, "", "Skipped", "hidden"))
        
        return results
    
    def _check_auto_verification(self, results: List[Dict], question: Dict, problem_type: str) -> bool:
        """Check if submission should be auto-verified"""
        if problem_type not in ["code_test", "code_codeplayground_test"]:
            return False
        
        hidden_results = [r for r in results if r["type"] == "hidden"]
        hidden_total = len(question.get("Hidden_Test_Cases", []))
        
        return (hidden_results and 
                all(r["status"] == "Passed" for r in hidden_results) and
                len(hidden_results) == hidden_total)
    
    def _auto_verify_submission(self, intern_id: str, question: Dict, source_code: str, problem_type: str) -> None:
        """Auto-verify successful submission"""
        question_id = str(question["_id"])
        subject = question.get("Subject", "").lower()
        tag = question.get("Tags", "").lower()
        
        self.verification_service.verify_question(
            intern_id, question_id, problem_type, subject, tag, True, source_code
        )
    
    def _auto_verify_sql_submission(self, intern_id: str, question: Dict, query: str, problem_type: str = "query_test") -> None:
        """Auto-verify successful SQL submission"""
        question_id = str(question["_id"])
        subject = question.get("Subject", "").lower()
        tag = question.get("Tags", "").lower()
        
        self.verification_service.verify_question(
            intern_id, question_id, problem_type, subject, tag, True, query
        )
    
    def _get_question(self, question_id: str, problem_type: str) -> Dict:
        """Get question by ID and type"""
        qid = InputValidator.validate_object_id(question_id)
        
        for collection_name in self.db.list_collection_names():
            if collection_name.endswith(f"_{problem_type}"):
                fields = {
                    "Hidden_Test_Cases": 1, "Sample_Input": 1, "Sample_Output": 1,
                    "Tags": 1, "Subject": 1
                }
                if problem_type in ["query_test", "query_codeplayground_test"]:
                    fields.update({"Input": 1, "Expected_Output": 1})
                
                question = self.find_one(collection_name, {"_id": qid}, fields)
                if question:
                    return question
        
        return None