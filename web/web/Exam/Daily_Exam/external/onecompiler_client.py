"""OneCompiler Client - External Service Integration (SoC)"""
import os
import requests
from typing import Dict, List, Any
from web.Exam.Daily_Exam.config.settings import ExternalServiceConfig
from web.Exam.Daily_Exam.utils.formatting import formatters
from web.Exam.Daily_Exam.utils.formatting.language_utils import language_to_ext
from web.Exam.Daily_Exam.utils.cache.cache_utils import hash_submission, submission_cache

class OneCompilerClient:
    """External service client for code execution"""
    
    def __init__(self):
        self.api_url = f"{ExternalServiceConfig.ONECOMPILER_API_URL}?access_token={ExternalServiceConfig.ONECOMPILER_ACCESS_TOKEN}"
        self.timeout = ExternalServiceConfig.ONECOMPILER_TIMEOUT
    

    
    def run_on_onecompiler(self, src: str, lang: str, stdin: Any) -> Dict[str, Any]:
        """Execute code on OneCompiler API"""
        lang_l, ext = language_to_ext(lang)
        payload = {
            "language": lang_l,
            "stdin": stdin if isinstance(stdin, list) else str(stdin),
            "files": [{"name": f"Main.{ext}", "content": src}]
        }
        r = requests.post(self.api_url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
    
    def execute_code(self, qid: str, src_code: str, lang: str, subject: str, 
                    sample_input: Any, sample_output: str, hidden_cases: List[Dict],
                    custom_enabled: bool, custom_input: str) -> Dict:
        """Execute code with original logic exactly"""
        from web.Exam.Daily_Exam.config.settings import SQL_SUBJECTS
        
        # Handle SQL Query execution
        if subject.lower() in SQL_SUBJECTS:
            return self.execute_sql_query(qid, src_code, sample_input, sample_output, custom_enabled, custom_input)
        
        # Cache lookup for non-custom runs
        if not custom_enabled:
            ck = hash_submission(qid, lang, src_code)
            cached = submission_cache.get(ck)
            if cached:
                cached["from_cache"] = True
                return cached
        
        results: List[Dict[str, Any]] = []
        sample_out = formatters.normalize_newlines(sample_output)
        
        # 1. Custom-input mode
        if custom_enabled:
            rc = self.run_on_onecompiler(src_code, lang, custom_input)
            out = formatters.normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            results.append({
                "input": custom_input,
                "expected_output": "",
                "actual_output": out,
                "status": "Custom Input",
                "type": "custom"
            })
            return {"message": "Custom input executed successfully", "results": results}
        
        # 2. Sample test
        if sample_input is not None:
            rc = self.run_on_onecompiler(src_code, lang, sample_input)
            out = formatters.normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            status = formatters.verdict(out, sample_out)
            results.append({
                "input": sample_input,
                "expected_output": sample_out,
                "actual_output": out,
                "status": status,
                "type": "sample"
            })
            if status == "Failed":
                # Pad skipped hidden tests
                for idx, tc in enumerate(hidden_cases):
                    results.append({
                        "index": idx,
                        "input": tc.get("Input"),
                        "expected_output": formatters.normalize_newlines(str(tc.get("Output", ""))),
                        "actual_output": None,
                        "status": "Skipped",
                        "type": "hidden"
                    })
                message = formatters.generate_execution_message(results)
                resp = {"message": message, "results": results}
                submission_cache.put(ck, resp)
                return resp
        
        # 3. Hidden tests (server-side fetched)
        ran_hidden = 0
        for idx, tc in enumerate(hidden_cases):
            if not tc:
                continue
            inp = tc.get("Input")
            exp = formatters.normalize_newlines(str(tc.get("Output", "")))
            rc = self.run_on_onecompiler(src_code, lang, inp)
            out = formatters.normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            status = formatters.verdict(out, exp)
            results.append({
                "index": idx,
                "input": inp,
                "expected_output": exp,
                "actual_output": out,
                "status": status,
                "type": "hidden"
            })
            ran_hidden += 1
            if status == "Failed":
                break
        
        # 4. Pad remaining hidden tests as skipped
        for idx in range(ran_hidden, len(hidden_cases)):
            tc = hidden_cases[idx]
            results.append({
                "index": idx,
                "input": tc.get("Input"),
                "expected_output": formatters.normalize_newlines(str(tc.get("Output", ""))),
                "actual_output": None,
                "status": "Skipped",
                "type": "hidden"
            })
        
        # Generate meaningful message based on results
        message = formatters.generate_execution_message(results)
        
        # Cache & respond
        resp = {"message": message, "results": results}
        if not custom_enabled:
            submission_cache.put(ck, resp)
        return resp
    
    def execute_sql_query(self, qid: str, query: str, schema_sql: str, expected_output: str, custom_enabled: bool, custom_input: str) -> Dict:
        """Execute SQL query with schema validation"""
        # Cache lookup for non-custom runs
        if not custom_enabled:
            ck = hash_submission(qid, "sql", query)
            cached = submission_cache.get(ck)
            if cached:
                cached["from_cache"] = True
                return cached
        
        results: List[Dict[str, Any]] = []
        
        # 1. Custom query mode
        if custom_enabled:
            full_sql = f"{schema_sql}\n\n-- Custom Query\n{custom_input}"
            rc = self.run_sql_on_onecompiler(full_sql)
            out = formatters.normalize_newlines(rc.get("stdout", ""))
            results.append({
                "input": custom_input,
                "expected_output": "",
                "actual_output": out,
                "status": "Custom Query",
                "type": "custom"
            })
            return {"message": "Custom SQL query executed successfully", "results": results}
        
        # 2. Main query test (single test - no hidden cases for SQL)
        full_sql = f"{schema_sql}\n\n-- User Query\n{query}"
        rc = self.run_sql_on_onecompiler(full_sql)
        out = formatters.normalize_newlines(rc.get("stdout", ""))
        expected = formatters.normalize_newlines(expected_output)
        status = formatters.verdict(out, expected)
        
        results.append({
            "input": query,
            "expected_output": expected,
            "actual_output": out,
            "status": status,
            "type": "query"
        })
        
        message = f"SQL query executed: {status}"
        resp = {"message": message, "results": results}
        
        # Cache the result for non-custom runs
        if not custom_enabled:
            submission_cache.put(ck, resp)
        
        return resp
    
    def run_sql_on_onecompiler(self, sql: str) -> Dict[str, Any]:
        """Execute SQL on OneCompiler API"""
        payload = {
            "language": "mysql",
            "files": [{"name": "query.sql", "content": sql}]
        }
        r = requests.post(self.api_url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()