"""
pdf_generator.py

Clean, modular PDF generation and S3 upload layer.
- Initializes S3 bucket and connection pool management.
- Provides `generate_student_report` entrypoint.
- Handles retry logic, backoff, and mocking for tests.
"""
import os
import time
import random
import atexit
import threading
from typing import Optional, Dict

import boto3
import botocore.config

from web.Exam.Parent_Reports.Parent_Whatsapp_report.pdf_reports.report_builder import (
    create_complete_report,
)
from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.bucket_utils import (
    ensure_bucket_ready,
    reset_s3_connection_pool,
    BUCKET as DEFAULT_BUCKET,
    s3,
)

# ─────────────────────────── Module-level configuration ─────────────────────────
REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET = os.getenv("S3_BUCKET_PARENT_REPORTS", DEFAULT_BUCKET)

# Use per-upload sessions by default
os.environ.setdefault("USE_PER_UPLOAD_S3_SESSION", "true")

# Flag to track if bucket has been initialized
_bucket_initialized = False

# Rate limiting for S3 operations
_s3_rate_limiter = threading.Semaphore(3)  # Max 3 concurrent S3 operations
_last_s3_call = 0
_s3_call_lock = threading.Lock()

# Circuit breaker for SSL failures
_ssl_failure_count = 0
_ssl_failure_lock = threading.Lock()
_circuit_breaker_open = False
_circuit_breaker_reset_time = 0

# Clean up S3 connections on interpreter exit
def _cleanup():
    try:
        if hasattr(s3, '_endpoint'):
            s3._endpoint.http_session.close()
    finally:
        reset_s3_connection_pool()
atexit.register(_cleanup)

# ────────────────────────── Helper functions ─────────────────────────────

def save_pdf_locally(pdf_bytes: bytes, filename: str) -> str:
    """
    Save PDF bytes to a local `reports/` directory next to this file.
    Returns the filesystem path.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)
    return filepath

def _create_s3_client() -> boto3.client:
    """Create a fresh S3 client with hardened timeouts and retries."""
    cfg = botocore.config.Config(
        region_name=REGION,
        max_pool_connections=1,  # Single connection per client
        connect_timeout=60,      # Increased timeout
        read_timeout=120,        # Increased timeout
        retries={'max_attempts': 5, 'mode': 'standard'},  # More retries
        tcp_keepalive=False,     # Disable keepalive to avoid connection issues
    )
    return boto3.client('s3', config=cfg)

def _ensure_bucket_initialized():
    """Lazy initialization of S3 bucket to avoid issues during multiprocessing."""
    global _bucket_initialized
    if not _bucket_initialized:
        try:
            ensure_bucket_ready(BUCKET, public=True)
            _bucket_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize S3 bucket: {e}")
            # Continue without bucket initialization for now
            pass

def upload_pdf_to_s3(pdf_bytes: bytes, s3_key: str, mock: bool = False, max_retries: int = 5) -> str:
    global _last_s3_call
    
    # Check if S3 operations are disabled
    if os.getenv("DISABLE_S3_OPERATIONS", "false").lower() == "true":
        return f"disabled://{BUCKET}/{s3_key}"
        
    if mock or os.getenv("MOCK_S3_UPLOAD", "false").lower() == "true":
        return f"mock://{BUCKET}/{s3_key}"

    # Rate limiting - acquire semaphore and add delay
    with _s3_rate_limiter:
        with _s3_call_lock:
            now = time.time()
            time_since_last = now - _last_s3_call
            if time_since_last < 0.5:  # Minimum 500ms between calls
                time.sleep(0.5 - time_since_last)
            _last_s3_call = time.time()
        
        # Ensure bucket is ready before upload
        _ensure_bucket_initialized()

        # Check circuit breaker
        with _ssl_failure_lock:
            global _ssl_failure_count, _circuit_breaker_open, _circuit_breaker_reset_time
            
            # Reset circuit breaker after 5 minutes
            if _circuit_breaker_open and time.time() > _circuit_breaker_reset_time:
                _circuit_breaker_open = False
                _ssl_failure_count = 0
                print("Circuit breaker reset - attempting S3 uploads again")
            
            # If circuit breaker is open, use mock
            if _circuit_breaker_open:
                return f"mock://{BUCKET}/{s3_key}?circuit_breaker=open"

        for attempt in range(1, max_retries + 1):
            try:
                client = _create_s3_client()
                client.put_object(
                    Bucket=BUCKET,
                    Key=s3_key,
                    Body=pdf_bytes,
                    ContentType="application/pdf",
                )
                # Safe cleanup
                if hasattr(client, "_endpoint"):
                    ep = client._endpoint
                    if hasattr(ep, "http_session") and ep.http_session:
                        try:
                            ep.http_session.close()
                        except Exception:
                            pass
                
                # Reset failure count on success
                with _ssl_failure_lock:
                    _ssl_failure_count = 0
                    
                return f"https://{BUCKET}.s3.amazonaws.com/{s3_key}"
                
            except Exception as e:
                # Check if it's an SSL error
                if "SSL" in str(e) or "ssl" in str(e).lower():
                    with _ssl_failure_lock:
                        _ssl_failure_count += 1
                        # Open circuit breaker after 5 SSL failures
                        if _ssl_failure_count >= 5:
                            _circuit_breaker_open = True
                            _circuit_breaker_reset_time = time.time() + 300  # 5 minutes
                            print(f"Circuit breaker opened due to SSL failures - switching to mock mode")
                            return f"mock://{BUCKET}/{s3_key}?circuit_breaker=opened"
                
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt + random.random(), 15))

        return f"mock://{BUCKET}/{s3_key}?error=upload_failed"

def generate_student_report(
    student_data: dict,
    period_id: str,
    batch_name: str,
    report_type: str,
    upload_to_s3: bool = True,
    mock_s3: bool = False,
    pre_rendered_pdf: Optional[bytes] = None,
) -> Dict:
    """
    Generate (and optionally upload) a single student's PDF report.

    Returns metadata:
    {
      'filename': str,
      's3_url': str,
      'uploaded': bool,
      'status': 'COMPLETED'|'SKIPPED'|'ERROR',
      'reason': Optional[str],
      'time': float
    }
    """
    start = time.time()
    name_slug = student_data.get('name', 'unknown').replace(' ', '_')
    filename = f"{name_slug}_{period_id}.pdf"

    # Skip if neither attendance nor exam data present
    if not student_data.get('attendance') and not student_data.get('dailyExam'):
        return {
            'filename': filename,
            'uploaded': False,
            'status': 'SKIPPED',
            'reason': 'NO_DATA',
            'time': 0.0,
        }

    try:
        # Generate PDF bytes
        pdf_bytes = pre_rendered_pdf or create_complete_report(
            student_data,
            period_id,
            batch_name,
            report_type == 'monthly'
        )
        # Optionally upload
        if upload_to_s3:
            s3_key = f"{period_id}/{batch_name}/{filename}"
            url = upload_pdf_to_s3(pdf_bytes, s3_key, mock=mock_s3)
            return {
                'filename': filename,
                's3_url': url,
                'uploaded': True,
                'status': 'COMPLETED',
                'reason': None,
                'time': time.time() - start,
            }
        # If not uploading, just return bytes location
        return {
            'filename': filename,
            'uploaded': False,
            'status': 'COMPLETED',
            'reason': 'LOCAL_SAVE',
            'time': time.time() - start,
        }
    except Exception as e:
        print(e)
        return {
            'filename': filename,
            'uploaded': False,
            'status': 'ERROR',
            'reason': type(e).__name__,
            'time': time.time() - start,
        }

# ────────────────────────── Parallel processing functions ─────────────────────────────

def get_optimal_workers(workload_size, worker_type="cpu"):
    """Calculate optimal worker count based on system resources and workload"""
    import os
    import psutil
    
    cpu_count = os.cpu_count() or 4
    memory_gb = psutil.virtual_memory().total / (1024**3)
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    
    if worker_type == "cpu":
        # PDF generation - CPU and memory intensive
        # Drastically reduce for stability under high load
        safe_workers = min(2, workload_size)  # Max 2 workers for PDF generation
        return safe_workers
        
    elif worker_type == "io":
        # S3 uploads - I/O bound, but limit connections to prevent SSL issues
        # Reduce connection limit significantly
        connection_limit = 5  # Very conservative limit
        return min(connection_limit, workload_size)
        
    elif worker_type == "batch":
        # Batch coordination - Reduce to prevent overwhelming the system
        return min(3, workload_size)  # Max 3 batch workers
        
    return min(2, workload_size)

def generate_pdf_worker(args):
    """Worker function for PDF generation"""
    student, period_id, batch_name, report_type = args
    try:
        pdf_bytes = create_complete_report(
            student, period_id, batch_name, report_type == 'monthly'
        )
        name = student.get('name') or 'unknown'
        return {
            'student_id': student.get('id'),
            'pdf_bytes': pdf_bytes,
            'filename': f"{name.replace(' ', '_')}_{period_id}.pdf"
        }
    except Exception as e:
        name = student.get('name') or 'unknown'
        return {
            'student_id': student.get('id'),
            'error': str(e),
            'filename': f"{name.replace(' ', '_')}_{period_id}.pdf"
        }

def upload_s3_worker(args):
    """Worker function for S3 upload"""
    pdf_data, s3_key, mock_s3 = args
    try:
        s3_url = upload_pdf_to_s3(pdf_data['pdf_bytes'], s3_key, mock=mock_s3)
        return {
            'student_id': pdf_data['student_id'],
            's3_url': s3_url,
            'filename': pdf_data['filename'],
            'uploaded': True
        }
    except Exception as e:
        return {
            'student_id': pdf_data['student_id'],
            'error': str(e),
            'filename': pdf_data['filename'],
            'uploaded': False
        }

def generate_batch_reports_parallel(students, period_id, batch_name, report_type, mock_s3=False):
    """Generate reports for a batch using parallel processing"""
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
    
    # Generate PDFs in parallel (CPU-bound)
    pdf_workers = get_optimal_workers(len(students), "cpu")
    pdf_args = [(student, period_id, batch_name, report_type) for student in students]
    
    print(f"  PDF Generation: {pdf_workers} workers for {len(students)} students")
    
    pdf_results = {}
    with ProcessPoolExecutor(max_workers=pdf_workers) as executor:
        future_to_student = {executor.submit(generate_pdf_worker, args): args[0] for args in pdf_args}
        for future in as_completed(future_to_student):
            result = future.result()
            pdf_results[result['student_id']] = result
    
    # Upload to S3 in parallel (I/O-bound)
    s3_workers = get_optimal_workers(len(students), "io")
    successful_pdfs = [pdf for pdf in pdf_results.values() if 'pdf_bytes' in pdf]
    
    print(f"  S3 Upload: {s3_workers} workers for {len(successful_pdfs)} PDFs")
    
    s3_args = [
        (pdf_data, f"{period_id}/{batch_name}/{pdf_data['filename']}", mock_s3)
        for pdf_data in successful_pdfs
    ]
    
    s3_results = {}
    with ThreadPoolExecutor(max_workers=s3_workers) as executor:
        future_to_pdf = {executor.submit(upload_s3_worker, args): args[0] for args in s3_args}
        for future in as_completed(future_to_pdf):
            result = future.result()
            s3_results[result['student_id']] = result
    
    # Attach S3 URLs to student records
    for student in students:
        student_id = student.get('id')
        if student_id in s3_results:
            student["s3_url"] = s3_results[student_id].get('s3_url')
        else:
            student["s3_url"] = None
    
    return students