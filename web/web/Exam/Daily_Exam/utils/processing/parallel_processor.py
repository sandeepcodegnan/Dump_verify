"""Universal Parallel Processing Utilities - Works on ALL Environments"""
import os
import platform
import threading
import time
from typing import Dict, List, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

# Optional dependencies with fallbacks
try:
    import psutil
except ImportError:
    psutil = None

try:
    import signal
    HAS_SIGNAL = hasattr(signal, 'SIGALRM')
except ImportError:
    signal = None
    HAS_SIGNAL = False

# Environment detection
SYSTEM = platform.system().lower()
IS_WINDOWS = SYSTEM == 'windows'
IS_LINUX = SYSTEM == 'linux'
IS_MACOS = SYSTEM == 'darwin'
IS_UNIX_LIKE = IS_LINUX or IS_MACOS


class ParallelProcessor:
    """Dynamic threading processor for exam paper building"""
    
    @staticmethod
    def calculate_optimal_workers(task_count: int, task_type: str = "general") -> int:
        """Universal worker calculation - works on ALL environments"""
        try:
            # Get CPU count with multiple fallbacks
            cpu_count = ParallelProcessor._get_cpu_count()
            
            # Get memory limit with fallbacks
            memory_limit = ParallelProcessor._get_memory_limit()
            
            # Environment-specific adjustments
            env_multiplier = ParallelProcessor._get_environment_multiplier()
            
            # Task-specific limits
            if task_type == "subject":
                base_workers = min(int(cpu_count * env_multiplier), 16)
                workload_limit = min(task_count, 8)
            elif task_type == "question":
                base_workers = min(cpu_count, 6)  # Conservative for DB
                workload_limit = min(task_count, 4)
            else:
                base_workers = min(cpu_count, 8)
                workload_limit = min(task_count, 6)
            
            # Final calculation with all constraints
            optimal_workers = min(base_workers, memory_limit, workload_limit)
            
            # Ensure reasonable bounds
            return max(min(optimal_workers, task_count), 1)
            
        except Exception as e:
            print(f"Worker calculation failed, using safe default: {e}")
            return min(max(task_count, 1), 3)  # Ultra-safe fallback
    
    @staticmethod
    def _get_cpu_count() -> int:
        """Get CPU count with multiple fallbacks"""
        try:
            # Primary method
            if hasattr(os, 'cpu_count') and os.cpu_count():
                return os.cpu_count()
            
            # Fallback methods
            if psutil:
                return psutil.cpu_count() or 4
            
            # Environment variable fallback
            if 'NUMBER_OF_PROCESSORS' in os.environ:
                return int(os.environ['NUMBER_OF_PROCESSORS'])
            
            # Last resort
            return 4
            
        except Exception:
            return 4  # Safe default
    
    @staticmethod
    def _get_memory_limit() -> int:
        """Get memory-based worker limit with fallbacks"""
        try:
            if psutil:
                memory_gb = psutil.virtual_memory().total / (1024**3)
                return max(int(memory_gb / 2), 2)  # Conservative
            
            # Environment-based estimation
            if IS_WINDOWS:
                return 8  # Conservative for Windows
            elif 'AWS' in os.environ.get('PATH', '').upper():
                return 4  # Very conservative for AWS
            else:
                return 6  # Default for unknown environments
                
        except Exception:
            return 4  # Ultra-safe default
    
    @staticmethod
    def _get_environment_multiplier() -> float:
        """Get environment-specific performance multiplier"""
        try:
            # Check for cloud environments
            if any(key in os.environ for key in ['AWS_REGION', 'AWS_LAMBDA_FUNCTION_NAME']):
                return 1.5  # AWS can handle more
            elif 'GOOGLE_CLOUD' in os.environ.get('PATH', '').upper():
                return 1.5  # GCP can handle more
            elif IS_WINDOWS:
                return 1.8  # Windows desktop usually has good resources
            elif IS_LINUX:
                return 2.0  # Linux servers are usually powerful
            else:
                return 1.5  # Conservative default
                
        except Exception:
            return 1.0  # No multiplier on error
    
    @staticmethod
    def process_with_timeout(tasks: List[Any], processor_func: Callable, 
                           timeout: int = 20, task_type: str = "general") -> List[Any]:
        """Universal parallel processing with timeout - works on ALL environments"""
        if not tasks:
            return []
        
        try:
            results = []
            start_time = time.time()
            
            # Calculate optimal workers
            max_workers = ParallelProcessor.calculate_optimal_workers(len(tasks), task_type)
            print(f"[{SYSTEM.upper()}] Using {max_workers} workers for {len(tasks)} {task_type} tasks")
            
            # Use different timeout strategies based on environment
            if len(tasks) == 1:
                # Single task - no need for complex parallel processing
                try:
                    result = processor_func(tasks[0])
                    if result:
                        results.append(result)
                except Exception as e:
                    task_name = getattr(tasks[0], 'get', lambda x, y: str(tasks[0]))('subject', str(tasks[0]))
                    print(f"Failed to process {task_name}: {str(e)}")
            else:
                # Multiple tasks - parallel processing
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_task = {}
                    
                    # Submit all tasks
                    for task in tasks:
                        future = executor.submit(processor_func, task)
                        future_to_task[future] = task
                    
                    # Collect results with universal timeout handling
                    completed_count = 0
                    for future in as_completed(future_to_task, timeout=timeout):
                        # Check overall timeout
                        if time.time() - start_time > timeout:
                            print(f"Overall timeout reached after {timeout} seconds")
                            break
                        
                        task = future_to_task[future]
                        try:
                            # Individual task timeout
                            individual_timeout = min(timeout // 2, 10)
                            result = future.result(timeout=individual_timeout)
                            if result:
                                results.append(result)
                            completed_count += 1
                        except Exception as e:
                            task_name = getattr(task, 'get', lambda x, y: str(task))('subject', str(task))
                            print(f"Task {task_name} failed: {str(e)}")
                            completed_count += 1
                            continue
            
            elapsed = time.time() - start_time
            print(f"Processing completed in {elapsed:.2f}s with {len(results)} successful results")
            
            return results
            
        except TimeoutError:
            elapsed = time.time() - start_time
            print(f"Processing timed out after {elapsed:.2f}s")
            raise ValueError("Processing is taking too long. Please try again in a moment.")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Parallel processing failed after {elapsed:.2f}s: {str(e)}")
            raise ValueError(f"Unable to process tasks. Please contact support if this persists.")
    
    @staticmethod
    def process_requests_parallel(requests: List[Dict], processor_func: Callable, 
                                timeout: int = 15) -> tuple:
        """Universal question fetch processing - works on ALL environments"""
        mcqs, second_questions = [], []
        
        if not requests:
            return mcqs, second_questions
        
        start_time = time.time()
        question_workers = ParallelProcessor.calculate_optimal_workers(len(requests), "question")
        
        try:
            if len(requests) == 1:
                # Single request - direct processing
                request = requests[0]
                try:
                    result = processor_func(request)
                    if request["type"] == "mcq":
                        mcqs.extend(result.get("mcq", []))
                    else:
                        second_questions.extend(result.get(request["type"], []))
                except Exception as e:
                    print(f"Failed to fetch {request['type']} questions: {str(e)}")
            else:
                # Multiple requests - parallel processing
                with ThreadPoolExecutor(max_workers=question_workers) as executor:
                    future_to_request = {}
                    
                    for request in requests:
                        future = executor.submit(processor_func, request)
                        future_to_request[future] = request
                    
                    # Collect results with universal timeout
                    completed = 0
                    for future in as_completed(future_to_request, timeout=timeout):
                        # Check overall timeout
                        if time.time() - start_time > timeout:
                            break
                        
                        request = future_to_request[future]
                        try:
                            # Individual timeout based on remaining time
                            remaining_time = timeout - (time.time() - start_time)
                            individual_timeout = min(max(remaining_time / 2, 1), 5)
                            
                            result = future.result(timeout=individual_timeout)
                            if request["type"] == "mcq":
                                mcqs.extend(result.get("mcq", []))
                            else:
                                second_questions.extend(result.get(request["type"], []))
                            completed += 1
                        except Exception as e:
                            print(f"Failed to fetch {request['type']} questions: {str(e)}")
                            completed += 1
                            continue
            
            elapsed = time.time() - start_time
            total_questions = len(mcqs) + len(second_questions)
            print(f"Question fetching completed in {elapsed:.2f}s: {total_questions} questions")
            
        except TimeoutError:
            elapsed = time.time() - start_time
            print(f"Question fetching timed out after {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Question fetching failed after {elapsed:.2f}s: {str(e)}")
        
        return mcqs, second_questions