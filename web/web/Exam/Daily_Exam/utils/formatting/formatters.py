"""Formatting utilities from legacy - DRY Implementation"""
from typing import Any, Optional, List, Dict

def normalize_newlines(text: Optional[str]) -> str:
    """
    Normalize text output from compilers
    Centralized version replacing duplicate normalize() functions
    """
    if text is None:
        return ""
    return (
        text.replace("↵", "\n")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .rstrip("\n")
    )

def verdict(actual: str, expected: str) -> str:
    """Compare actual vs expected output from legacy"""
    return "Passed" if normalize_newlines(actual) == normalize_newlines(expected) else "Failed"

def format_duration(seconds: int) -> str:
    """Format seconds to HH:MM:SS"""
    if seconds < 0:
        return "00:00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def sanitize_exam_fields(question: dict, question_type: str) -> dict:
    """Format questions to match frontend expectations (clean format)"""
    if question_type == "MCQ":
        return {
            "questionId": question["questionId"],  # Always exists from pipeline
            "Question": question.get("Question", ""),
            "Options": question.get("Options", {}),
            "Difficulty": question.get("Difficulty", ""),
            "Tags": question.get("Tags", ""),
            "Question_Type": "mcq",
            "Subject": question.get("Subject").lower(),
            "Image_URL": question.get("Image_URL")
        }
    elif question_type == "Coding":
        return {
            "questionId": question["questionId"],  # Always exists from pipeline
            "Question": question.get("Question", ""),
            "Sample_Input": question.get("Sample_Input", ""),
            "Sample_Output": question.get("Sample_Output", ""),
            "Difficulty": question.get("Difficulty", ""),
            "Tags": question.get("Tags", ""),
            "Question_Type": "code",
            "Subject": question.get("Subject", "python").lower(),
            "Constraints": question.get("Constraints", "1 ≤ input ≤ 1000"),
            "Question_No": question.get("Question_No", 1)
        }
    elif question_type == "Query":
        return {
            "questionId": question["questionId"],  # Always exists from pipeline
            "Question": question.get("Question", ""),
            "Input": question.get("Input", ""),
            "Expected_Output": question.get("Expected_Output", ""),
            "Input_Structured": question.get("Input_Structured", {}),
            "Difficulty": question.get("Difficulty", ""),
            "Tags": question.get("Tags", ""),
            "Question_Type": "query",
            "Subject": question.get("Subject", "mysql").lower(),
            "Question_No": question.get("Question_No", 1)
        }
    return question



def generate_execution_message(results: List[Dict]) -> str:
    """Generate meaningful message based on test execution results"""
    if not results:
        return "No test cases executed"
    
    # Count test results
    total_tests = len([r for r in results if r.get("type") != "custom"])
    passed_tests = len([r for r in results if r.get("status") == "Passed"])
    failed_tests = len([r for r in results if r.get("status") == "Failed"])
    skipped_tests = len([r for r in results if r.get("status") == "Skipped"])
    
    if total_tests == 0:
        return "Compilation completed"
    
    # All tests passed
    if passed_tests == total_tests:
        return f"Compilation completed successfully with all {total_tests} test cases passed"
    
    # Some tests failed
    if failed_tests > 0:
        return f"Compilation completed with {passed_tests} out of {total_tests} test cases passed"
    
    # Only skipped tests (shouldn't happen normally)
    return f"Compilation completed with {passed_tests} test cases passed"