"""
Code Execution Service
Centralized OneCompiler integration following DRY principle
"""
import requests
from typing import Dict, List, Union
from web.Exam.Testing.config.testing_config import ONECOMPILER_CONFIG, LANGUAGE_EXTENSIONS
from web.Exam.Testing.utils.formatters import normalize_text
from web.Exam.Testing.exceptions.testing_exceptions import ExecutionError, ValidationError

class ExecutionService:
    """Centralized code execution service"""
    
    def __init__(self):
        self.config = ONECOMPILER_CONFIG
        self.api_url = f"{self.config['api_url']}?access_token={self.config['access_token']}"
        self.extensions = LANGUAGE_EXTENSIONS
    
    def execute_code(self, source: str, language: str, stdin: Union[str, List[str]]) -> Dict:
        """Execute code with OneCompiler API"""
        if not self.config['access_token']:
            raise ExecutionError("OneCompiler access token not configured")
        
        language = self._normalize_language(language)
        extension = self.extensions.get(language, "txt")
        
        if isinstance(stdin, list):
            return self._execute_batch(source, language, extension, stdin)
        else:
            return self._execute_single(source, language, extension, stdin)
    
    def execute_sql(self, query: str, schema_sql: str, validate_tables: bool = True) -> Dict:
        """Execute SQL query with schema and table validation"""
        if not schema_sql:
            raise ValidationError("SQL schema is required")
        
        # Validate tables if requested
        if validate_tables:
            self._validate_sql_tables(query, schema_sql)
        
        # Auto-detect JOIN queries
        has_join = self._detect_join_query(query)
        
        full_sql = f"{schema_sql}\n\n-- User Query\n{query}"
        payload = {
            "language": "mysql",
            "files": [{"name": "queries.sql", "content": full_sql}]
        }
        
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=self.config['timeout_sql']
            )
            response.raise_for_status()
            result = response.json()
            
            stdout = normalize_text(result.get("stdout", ""))
            stderr = normalize_text(result.get("stderr", ""))
            
            # Handle empty results dynamically
            if not stdout and not stderr:
                if has_join:
                    stdout = "Empty set (0.00 sec)"
                elif self._is_select_query(query):
                    stdout = "Empty set (0.00 sec)"
                elif self._is_modification_query(query):
                    stdout = "Query OK, 0 rows affected (0.00 sec)"
            
            # Enhance error messages
            if stderr:
                stderr = self._enhance_sql_error_message(stderr)
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "success": not stderr,
                "query_type": self._get_query_type(query, has_join)
            }
        except requests.RequestException as e:
            raise ExecutionError(f"SQL execution failed: {str(e)}")
    
    def _normalize_language(self, language: str) -> str:
        """Normalize language name"""
        lang = (language or "").lower()
        return "cpp" if lang == "c++" else lang
    
    def _execute_single(self, source: str, language: str, extension: str, stdin: str) -> Dict:
        """Execute single test case"""
        payload = {
            "language": language,
            "stdin": str(stdin),
            "files": [{"name": f"Main.{extension}", "content": source}]
        }
        
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=self.config['timeout_code']
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "stdout": normalize_text(result.get("stdout", "")),
                "stderr": normalize_text(result.get("stderr", "")),
                "success": True
            }
        except requests.RequestException as e:
            raise ExecutionError(f"Code execution failed: {str(e)}")
    
    def _execute_batch(self, source: str, language: str, extension: str, stdin_list: List[str]) -> List[Dict]:
        """Execute multiple test cases"""
        results = []
        for stdin in stdin_list:
            try:
                result = self._execute_single(source, language, extension, stdin)
                results.append(result)
            except ExecutionError:
                # Continue with other test cases on individual failures
                results.append({
                    "stdout": "",
                    "stderr": "Execution failed",
                    "success": False
                })
        return results
    
    def _validate_sql_tables(self, query: str, schema_sql: str) -> None:
        """Validate SQL query tables against schema"""
        # Extract table names from query
        query_tables = self._extract_query_tables(query)
        
        # Extract available tables from schema
        available_tables = self._extract_schema_tables(schema_sql)
        
        # Validate query requirements vs available tables
        if query_tables and not query_tables.issubset(available_tables):
            missing_tables = query_tables - available_tables
            raise ValidationError(f"Required tables not found: {list(missing_tables)}")
    
    def _extract_query_tables(self, query: str) -> set:
        """Extract table names from SQL query"""
        import re
        
        query_upper = query.upper()
        table_patterns = [
            r'FROM\s+(\w+)',
            r'(?:NATURAL\s+)?(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+|CROSS\s+)?JOIN\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'INSERT\s+INTO\s+(\w+)',
            r'DELETE\s+FROM\s+(\w+)'
        ]
        
        query_tables = set()
        for pattern in table_patterns:
            matches = re.findall(pattern, query_upper)
            query_tables.update(matches)
        
        return query_tables
    
    def _extract_schema_tables(self, schema_sql: str) -> set:
        """Extract table names from CREATE TABLE statements"""
        import re
        
        create_table_matches = re.findall(r'CREATE\s+TABLE\s+(\w+)', schema_sql.upper())
        return set(create_table_matches)
    
    def _detect_join_query(self, query: str) -> bool:
        """Auto-detect JOIN queries dynamically"""
        import re
        query_upper = query.upper()
        
        # Comprehensive JOIN pattern matching
        join_patterns = [
            r'\bJOIN\b',
            r'\bINNER\s+JOIN\b',
            r'\bLEFT\s+(?:OUTER\s+)?JOIN\b',
            r'\bRIGHT\s+(?:OUTER\s+)?JOIN\b',
            r'\bFULL\s+(?:OUTER\s+)?JOIN\b',
            r'\bCROSS\s+JOIN\b',
            r'\bNATURAL\s+(?:INNER\s+|LEFT\s+|RIGHT\s+)?JOIN\b'
        ]
        
        return any(re.search(pattern, query_upper) for pattern in join_patterns)
    
    def _enhance_sql_error_message(self, error: str) -> str:
        """Enhance SQL error messages with helpful suggestions"""
        if "Failed to open the referenced table" in error:
            return "Create parent tables before child tables with foreign keys"
        elif "STRING_AGG" in error.upper():
            return "Use GROUP_CONCAT instead of STRING_AGG in MySQL"
        elif "ISNULL" in error.upper() and "function" in error.lower():
            return "Use IFNULL or COALESCE instead of ISNULL in MySQL"
        elif "TOP" in error.upper() and "syntax" in error.lower():
            return "Use LIMIT instead of TOP in MySQL"
        elif "WITH" in error.upper() and "syntax" in error.lower():
            return "CTE (WITH clause) requires MySQL 8.0+. Use subqueries for older versions"
        elif "TIMESTAMPDIFF" in error.upper() and "syntax error" in error.lower():
            return "Check TIMESTAMPDIFF syntax: TIMESTAMPDIFF(unit, start_date, end_date)"
        elif "doesn't exist" in error.lower():
            return "Table doesn't exist. Check table name and ensure schema is provided."
        elif "ambiguous" in error.lower():
            return "Column reference is ambiguous. Use table aliases or fully qualified column names."
        elif "unknown column" in error.lower():
            return "Column not found. Check column name and table structure."
        else:
            return error
    
    def _is_select_query(self, query: str) -> bool:
        """Check if query is a SELECT statement"""
        return query.strip().upper().startswith('SELECT')
    
    def _is_modification_query(self, query: str) -> bool:
        """Check if query modifies data (INSERT, UPDATE, DELETE)"""
        query_upper = query.strip().upper()
        return any(query_upper.startswith(cmd) for cmd in ['INSERT', 'UPDATE', 'DELETE'])
    
    def _get_query_type(self, query: str, has_join: bool) -> str:
        """Dynamically determine query type"""
        query_upper = query.strip().upper()
        
        if has_join:
            if 'NATURAL' in query_upper:
                return "natural_join_query"
            elif any(join_type in query_upper for join_type in ['LEFT', 'RIGHT', 'FULL']):
                return "outer_join_query"
            elif 'CROSS' in query_upper:
                return "cross_join_query"
            else:
                return "inner_join_query"
        elif query_upper.startswith('SELECT'):
            if 'GROUP BY' in query_upper:
                return "aggregate_query"
            elif 'ORDER BY' in query_upper:
                return "sorted_query"
            else:
                return "simple_select_query"
        elif query_upper.startswith(('INSERT', 'UPDATE', 'DELETE')):
            return "modification_query"
        else:
            return "other_query"
    
    def validate_sql_query(self, query: str, available_tables: List[str]) -> bool:
        """Validate SQL query against available tables"""
        query_tables = self._extract_query_tables(query)
        return query_tables.issubset(set(t.upper() for t in available_tables))