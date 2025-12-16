"""
Report processing service: orchestrates batch/location/global processing
"""
import argparse
import time
from web.Exam.exam_central_db import db
from web.Exam.Parent_Reports.Parent_Whatsapp_report.reports.pipeline import process_batch
from web.Exam.Parent_Reports.Parent_Whatsapp_report.core.infrastructure.report_repository import ReportRepository
from web.Exam.Parent_Reports.Parent_Whatsapp_report.core.adapters.status_tracker_adapter import StatusTrackerAdapter


def get_active_batches(location=None, batch_name=None):
    repo = ReportRepository(db)
    return repo.get_active_batches(location=location, batch_name=batch_name)


def _get_or_compute_period_id(report_type, period_id=None, start_date=None, end_date=None):
    if period_id:
        return period_id, start_date, end_date
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
    start_date_calc, end_date_calc = get_report_config(report_type)["date_calculator"]()
    return f"{start_date_calc}_to_{end_date_calc}", start_date_calc, end_date_calc


def _precheck_existing_status(report_type, period_id, location, batch, force):
    if force:
        return None
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import ReportStatusTracker
    tracker = ReportStatusTracker(report_type, period_id)
    status = tracker.get_status()
    if not status:
        return None
    if location and batch:
        batch_pdf_status = status.get("locations", {}).get(location, {}).get("batches", {}).get(batch, {}).get("pdf", {}).get("status")
        if batch_pdf_status == "COMPLETED":
            return {
                "success": True,
                "message": f"PDF already completed for batch {batch} in {location}. Use --force to regenerate.",
                "summary": {
                    "total_batches": 0,
                    "successful_batches": 0,
                    "failed_batches": 0,
                    "skipped_batches": 0,
                    "processed_batches": 0,
                    "total_students": 0
                },
                "results": []
            }
    elif location:
        location_pdf_status = status.get("locations", {}).get(location, {}).get("pdf", {}).get("status")
        if location_pdf_status == "COMPLETED":
            return {
                "success": True,
                "message": f"PDF already completed for location {location}. Use --force to regenerate.",
                "summary": {
                    "total_batches": 0,
                    "successful_batches": 0,
                    "failed_batches": 0,
                    "skipped_batches": 0,
                    "processed_batches": 0,
                    "total_students": 0
                },
                "results": []
            }
    else:
        global_pdf_status = status.get("global_pdf", {}).get("status")
        if global_pdf_status in ["COMPLETED", "PARTIAL"]:
            return {
                "success": True,
                "message": f"PDF processing already {global_pdf_status.lower()}. Use --force to regenerate.",
                "summary": {
                    "total_batches": 0,
                    "successful_batches": 0,
                    "failed_batches": 0,
                    "skipped_batches": 0,
                    "processed_batches": 0,
                    "total_students": 0
                },
                "results": []
            }
    return None


def process_single_batch_wrapper(args):
    batch_info, report_type, force, period_id, start_date, end_date = args
    try:
        result = process_batch(
            report_type=report_type,
            location=batch_info["location"],
            batch_name=batch_info["Batch"],
            period_id=period_id,
            start_date=start_date,
            end_date=end_date,
            mock_s3=False,
            force=force
        )
        result["batch_info"] = batch_info
        return result
    except Exception as e:
        return {
            "batch_info": batch_info,
            "success": False,
            "error": str(e),
            "status": "ERROR"
        }


def process_reports(report_type, location=None, batch=None, force=False, 
                   period_id=None, start_date=None, end_date=None):
    period_id, start_date, end_date = _get_or_compute_period_id(report_type, period_id, start_date, end_date)
    precheck = _precheck_existing_status(report_type, period_id, location, batch, force)
    if precheck:
        return precheck

    from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.tracker_manager import TrackerManager
    tracker, period_id = TrackerManager.initialize_tracker(report_type, period_id)
    start_time = time.time()

    if location and batch:
        print(f"Processing specific batch: {batch} in {location}")
        batches = get_active_batches(location=location, batch_name=batch)
        if not batches:
            return {
                "success": False,
                "message": f"Batch {batch} not found or not active in {location}",
                "results": []
            }
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.orchestration.processing_orchestrator import ProcessingOrchestrator
        orchestrator = ProcessingOrchestrator(report_type, force)
        results = orchestrator.process_location_batches(batches, period_id, start_date, end_date, tracker)
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        total_students = sum(r.get("processed", 0) for r in results)
        skipped_batches = sum(1 for r in results if r.get("status") == "SKIPPED")
        processed_batches = successful - skipped_batches
        total_time = time.time() - start_time
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.message_formatter import MessageFormatter
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import create_stats_object, create_batch_stats_object
        detailed_message = MessageFormatter.format_completion_message(
            total_students, 1, processed_batches, total_time
        )
        global_pdf_stats = create_stats_object(
            status="COMPLETED" if failed == 0 else "PARTIAL",
            success=total_students,
            error=failed,
            skipped=0,
            time_s=total_time,
            message=detailed_message
        )
        global_batch_stats = create_batch_stats_object(
            status="COMPLETED" if failed == 0 else "PARTIAL",
            total=len(results),
            pdf_completed=processed_batches,
            whatsapp_completed=0,
            skipped=skipped_batches,
            time_s=total_time,
            message=MessageFormatter.format_batch_message(processed_batches, skipped_batches, len(results))
        )
        StatusTrackerAdapter(tracker).set_location_pdf_completed(location)
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.stats_factory import StatsFactory
        final_location_stats = StatsFactory.create_final_location_stats(location, total_time)
        tracker.update_global_status(pdf_stats=global_pdf_stats, batch_stats=global_batch_stats, location_stats=final_location_stats)
        tracker.add_timeline_event("PROCESSING_COMPLETED", {
            "total_batches": len(results),
            "successful": successful,
            "failed": failed,
            "total_students": total_students,
            "processing_time": total_time
        })
        return {
            "success": True,
            "message": f"Processed specific batch {batch}: {successful} successful, {failed} failed. Total students: {total_students}",
            "summary": {
                "total_batches": len(results),
                "successful_batches": successful,
                "failed_batches": failed,
                "skipped_batches": skipped_batches,
                "processed_batches": processed_batches,
                "total_students": total_students
            },
            "results": results
        }
    elif location:
        print(f"Processing all active batches in location: {location}")
        batches = get_active_batches(location=location)
        if not batches:
            return {"success": False, "message": f"No active batches found in {location}", "results": []}
    else:
        print("Processing all active batches in all locations (location by location)")
        repo = ReportRepository(db)
        locations = repo.get_active_locations()
        if not locations:
            return {"success": False, "message": "No active locations found", "results": []}
        print(f"Found {len(locations)} locations to process: {locations}")
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import create_stats_object
        current_status = tracker.get_status() or {}
        global_pdf_status = current_status.get("global_pdf", {}).get("status")
        if global_pdf_status not in ["COMPLETED","PARTIAL"]:
            tracker.update_global_status(
                pdf_stats=create_stats_object(status="PROCESSING", success=0, error=0, skipped=0, message="PDF processing started")
            )
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.stats_factory import StatsFactory
        location_stats = StatsFactory.create_location_processing_stats(len(locations))
        tracker.update_global_status(location_stats=location_stats)
        all_results = []
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.orchestration.processing_orchestrator import ProcessingOrchestrator
        orchestrator = ProcessingOrchestrator(report_type, force)
        for current_location in locations:
            print(f"\n--- Processing Location: {current_location} ---")
            location_batches = get_active_batches(location=current_location)
            if not location_batches:
                print(f"No active batches in {current_location}, skipping...")
                continue
            print(f"Found {len(location_batches)} batches in {current_location}")
            current_status = tracker.get_status() or {}
            location_pdf_status = current_status.get("locations", {}).get(current_location, {}).get("pdf", {}).get("status")
            if location_pdf_status not in ["COMPLETED","PARTIAL"]:
                tracker.update_location_status(current_location, pdf_stats=create_stats_object(status="PROCESSING", success=0, error=0, skipped=0, message=f"Processing batches in {current_location}..."))
            location_results = orchestrator.process_location_batches(location_batches, period_id, start_date, end_date, tracker)
            all_results.extend(location_results)
            StatusTrackerAdapter(tracker).set_location_pdf_completed(current_location)
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.stats_factory import StatsFactory as SF
            loc_stats = SF.create_location_completion_stats()
            loc_stats["message"] = f"Completed {current_location}"
            tracker.update_global_status(location_stats=loc_stats)
        results = all_results
        batches = []

    if location and not batch:
        print(f"Found {len(batches)} active batches to process")
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import create_stats_object
        current_status = tracker.get_status() or {}
        global_pdf_status = current_status.get("global_pdf", {}).get("status")
        if global_pdf_status not in ["COMPLETED","PARTIAL"]:
            tracker.update_global_status(pdf_stats=create_stats_object(status="PROCESSING", success=0, error=0, skipped=0, message="PDF processing started"))
        tracker.add_timeline_event("PROCESSING_STARTED", {"location": location, "batch": batch, "total_batches": len(batches)})
        current_status = tracker.get_status() or {}
        current_locations = current_status.get("locations", {})
        is_new_location = location not in current_locations
        location_pdf_status = current_status.get("locations", {}).get(location, {}).get("pdf", {}).get("status")
        if location_pdf_status not in ["COMPLETED","PARTIAL"]:
            tracker.update_location_status(location, pdf_stats=create_stats_object(status="PROCESSING", success=0, error=0, skipped=0, message=f"Processing batches in {location}..."))
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.stats_factory import StatsFactory
        location_stats = StatsFactory.create_single_location_stats(location, is_new_location)
        tracker.update_global_status(location_stats=location_stats)
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.orchestration.processing_orchestrator import ProcessingOrchestrator
        orchestrator = ProcessingOrchestrator(report_type, force)
        results = orchestrator.process_location_batches(batches, period_id, start_date, end_date, tracker)

    if 'results' not in locals():
        results = []

    successful = sum(1 for r in results if r.get("success", False))
    failed = len(results) - successful
    total_students = sum(r.get("processed", 0) for r in results)
    skipped_batches = sum(1 for r in results if r.get("status") == "SKIPPED")
    processed_batches = successful - skipped_batches
    total_time = time.time() - start_time
    current_status = tracker.get_status() or {}
    current_global = current_status.get("global_pdf", {"success": 0})
    cumulative_students = current_global.get("success", 0) + total_students
    all_locations = set()
    if current_status.get("locations"):
        all_locations.update(current_status["locations"].keys())
    all_locations.update(r.get("batch_info", {}).get("location") for r in results if r.get("success"))
    total_locations_processed = len(all_locations)
    current_global_batches = current_status.get("global_batches", {"pdf_completed": 0})
    cumulative_completed_batches = current_global_batches.get("pdf_completed", 0) + processed_batches
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.message_formatter import MessageFormatter
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import create_stats_object, create_batch_stats_object
    detailed_message = MessageFormatter.format_completion_message(cumulative_students, total_locations_processed, cumulative_completed_batches, total_time)
    error_batches = sum(1 for r in results if r.get("status") == "ERROR")
    skipped_students = sum(r.get("processed", 0) for r in results if r.get("status") == "SKIPPED")
    global_pdf_stats = create_stats_object(status="COMPLETED" if failed == 0 else "PARTIAL", success=total_students - skipped_students, error=error_batches, skipped=skipped_students, time_s=total_time, message=detailed_message)
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.tracking.processing_status_tracker import create_batch_stats_object
    global_batch_stats = create_batch_stats_object(status="COMPLETED" if failed == 0 else "PARTIAL", total=len(results), pdf_completed=processed_batches, whatsapp_completed=0, skipped=skipped_batches, time_s=total_time, message=MessageFormatter.format_batch_message(processed_batches, skipped_batches, len(results)))
    if location:
        StatusTrackerAdapter(tracker).set_location_pdf_completed(location)
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.stats_factory import StatsFactory
    final_location_stats = StatsFactory.create_final_location_stats(location, total_time)
    tracker.update_global_status(pdf_stats=global_pdf_stats, batch_stats=global_batch_stats, location_stats=final_location_stats)
    tracker.add_timeline_event("PROCESSING_COMPLETED", {"total_batches": len(results), "successful": successful, "failed": failed, "total_students": total_students, "processing_time": total_time})
    return {
        "success": True,
        "message": f"Processed {len(results)} batches: {successful} successful, {failed} failed. Total students: {total_students}",
        "summary": {
            "total_batches": len(results),
            "successful_batches": successful,
            "failed_batches": failed,
            "skipped_batches": skipped_batches,
            "processed_batches": processed_batches,
            "total_students": total_students
        },
        "results": results
    }
