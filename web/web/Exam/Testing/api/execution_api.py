"""
Code Execution API - Refactored with Enterprise Architecture
Following SoC and DRY principles
"""
from flask import request
from flask_restful import Resource
from web.jwt.auth_middleware import tester_required
from web.Exam.Testing.services.execution_service import ExecutionService
from web.Exam.Testing.utils.validators import InputValidator
from web.Exam.Testing.exceptions.testing_exceptions import ValidationError

class ExecutionAPI(Resource):
    """Refactored Code Execution API"""
    
    def __init__(self):
        self.execution_service = ExecutionService()
    
    @tester_required
    def post(self):
        """Execute code or SQL"""
        try:
            data = request.get_json(force=True)
            language = data.get("language", "").lower()
            
            if language in ("mysql", "sql"):
                return self._handle_sql_execution(data)
            else:
                return self._handle_code_execution(data)
                
        except Exception as e:
            return {"success": False, "message": str(e)}, 400
    
    def _handle_sql_execution(self, data):
        """Handle SQL query execution"""
        required_fields = ["source_code", "language"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing field: {field}")
        
        query = data["source_code"]
        schema_sql = data.get("raw_table_sql", "")
        
        if not schema_sql:
            raise ValidationError("Missing field: 'raw_table_sql' required")
        
        # Execute SQL with validation
        result = self.execution_service.execute_sql(query, schema_sql, validate_tables=True)
        
        # Build response
        response = {
            "status": "success",
            "message": "MySQL query executed",
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
            "query_type": result.get("query_type", "simple_query")
        }
        
        # Add metadata if available
        if data.get("tables"):
            response["tables"] = data["tables"]
        
        return response, 200
    
    def _handle_code_execution(self, data):
        """Handle programming language execution"""
        required_fields = ["source_code", "language", "test_cases"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing field: {field}")
        
        source = data["source_code"]
        language = data["language"]
        test_cases = data["test_cases"]
        
        # Validate test cases
        InputValidator.validate_test_cases(test_cases)
        
        # Execute code
        results = []
        for test_case in test_cases:
            exec_result = self.execution_service.execute_code(source, language, test_case)
            results.append({
                "input": test_case,
                "output": exec_result.get("stdout", "")
            })
        
        response = {
            "status": "success",
            "message": "Code executed successfully",
            "results": results
        }
        
        return response, 200