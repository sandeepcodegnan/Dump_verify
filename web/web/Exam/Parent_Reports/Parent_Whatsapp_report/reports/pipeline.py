from web.Exam.exam_central_db import db
from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.date_utils import parse_period_id
from web.Exam.Parent_Reports.Parent_Whatsapp_report.data_aggregator import fetch_batch_report_docs


def should_process_batch(report_type, location, batch_name, period_id, force=False):
    """Check if batch should be processed"""
    if force:
        return True  # Skip all checks if force enabled
    
    # Check if report already exists in DB
    existing = db["parent_whatapp_report"].find_one({
        "period_id": period_id,
        "report_type": report_type,
        f"locations.{location}.{batch_name}": {"$exists": True}
    })
    
    return existing is None  # Process only if doesn't exist

def process_batch(
    report_type: str,
    location: str,
    batch_name: str,
    period_id: str=None,
    start_date: str = None,
    end_date: str = None,
    mock_s3: bool = False,
    force: bool = False
) -> dict:
    """
    Process a single batch: fetch data, skip if no records or no relevant data,
    generate & upload PDFs for students with attendance or exam data,
    and write updated list back to MongoDB in one atomic operation.

    Returns a dict with status_code, success flag, status message, and counts.
    """
    import time
    start_time = time.time()
    # 1) Determine date range
    if period_id:
        dt_start, dt_end = parse_period_id(period_id)
        start_date, end_date = dt_start.strftime("%Y-%m-%d"), dt_end.strftime("%Y-%m-%d")
    elif start_date and end_date:
        start_date, end_date = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        period_id = f"{start_date}_to_{end_date}"
    else:
        start_date, end_date = get_report_config(report_type)["date_calculator"]()
        period_id = f"{start_date}_to_{end_date}"
    
    # 1.5) Check if batch should be processed (idempotency)
    if not should_process_batch(report_type, location, batch_name, period_id, force):
        processing_time = time.time() - start_time
        return {
            "status_code": 200,
            "success": True,
            "status": "SKIPPED",
            "message": f"Report already exists for {batch_name}. Use --force to regenerate.",
            "processed": 0,
            "time": processing_time
        }

    # 2) Fetch all student data for this batch
    students = fetch_batch_report_docs(batch_name, location, start_date, end_date)
    if not students:
        processing_time = time.time() - start_time
        return {
            "status_code": 204,
            "success": False,
            "status": "NO_DATA",
            "message": "No student records found for this batch.",
            "processed": 0,
            "time": processing_time
        }

    # 3) Batch-wise check: skip entire batch if no one has attendance or exam
    if all(not rec.get("attendance") and not rec.get("dailyExam") for rec in students):
        processing_time = time.time() - start_time
        return {
            "status_code": 200,
            "success": True,
            "status": "SKIPPED",
            "message": f"Batch {batch_name} has no attendance or exam data to process.",
            "processed": 0,
            "time": processing_time
        }

    # 4) Filter students who have at least attendance or exam data
    valid_students = [
        rec for rec in students
        if rec.get("attendance") or rec.get("dailyExam")
    ]

    # 5) Generate & upload PDFs using parallel processing
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.services.pdf_generation_service import generate_batch_reports_parallel
    valid_students = generate_batch_reports_parallel(valid_students, period_id, batch_name, report_type, mock_s3)

    # 8) Write the entire updated list back to MongoDB in one atomic update
    coll = db["parent_whatapp_report"]
    filter_doc = {"period_id": period_id, "report_type": report_type}
    array_path = f"locations.{location}.{batch_name}"
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            result = coll.update_one(
                filter_doc,
                {"$set": {array_path: valid_students}},
                upsert=True
            )
            break
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                processing_time = time.time() - start_time
                return {
                    "status_code": 500,
                    "success": False,
                    "status": "DB_ERROR",
                    "message": f"Database update failed after {MAX_RETRIES} attempts: {e}",
                    "processed": len(valid_students),
                    "time": processing_time
                }
            import time
            time.sleep(0.5 * (attempt + 1))  # Exponential backoff

    processing_time = time.time() - start_time
    return {
        "status_code": 200,
        "success": True,
        "status": "COMPLETED",
        "message": f"Successfully processed {len(valid_students)} students.",
        "processed": len(valid_students),
        "time": processing_time,
        "matched": getattr(result, 'matched_count', 0),
        "modified": getattr(result, 'modified_count', 0)
    }

if __name__=="__main__":
    import time
    start=time.time()
    reqs1 = process_batch("weekly","vijayawada","PFS-VIJ-013")
    print(f"Time taken for weekly: {time.time()-start} seconds")
    start = time.time()
    reqs2 = process_batch("monthly","vijayawada","PFS-VIJ-013")
    print(f"Time taken for montly: {time.time()-start} seconds")
