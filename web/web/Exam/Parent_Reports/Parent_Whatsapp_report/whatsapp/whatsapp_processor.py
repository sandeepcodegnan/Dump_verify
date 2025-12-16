"""
WhatsApp processing based on PDF status and reports
"""
from web.Exam.exam_central_db import db
from web.Exam.Parent_Reports.Parent_Whatsapp_report.whatsapp.central_whatsapp_sender import send_batch_whatsapp_messages
from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker, create_stats_object


def process_whatsapp_for_batch(location: str, batch_name: str, period_id: str, report_type: str, tracker) -> dict:
    """Process WhatsApp sending for a specific batch based on PDF status"""
    import time
    start_time = time.time()
    
    # Check if WhatsApp already sent for this batch
    status = tracker.get_status()
    if status:
        batch_whatsapp_status = status.get("locations", {}).get(location, {}).get("batches", {}).get(batch_name, {}).get("whatsapp", {}).get("status")
        if batch_whatsapp_status == "COMPLETED":
            return {
                "success": True,
                "status": "SKIPPED",
                "message": f"WhatsApp already sent for batch {batch_name}",
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "time": 0
            }
    
    # Get students with completed PDFs from database
    report_doc = db["parent_whatapp_report"].find_one({
        "period_id": period_id,
        "report_type": report_type,
        f"locations.{location}.{batch_name}": {"$exists": True}
    })
    
    if not report_doc:
        return {
            "success": False,
            "status": "NO_DATA",
            "message": f"No PDF data found for batch {batch_name}",
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "time": time.time() - start_time
        }
    
    # Get students from the specific batch
    students = report_doc.get("locations", {}).get(location, {}).get(batch_name, [])
    
    if not students:
        return {
            "success": False,
            "status": "NO_STUDENTS",
            "message": f"No students found in batch {batch_name}",
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "time": time.time() - start_time
        }
    
    # Filter students who have PDFs (s3_url exists)
    students_with_pdfs = [s for s in students if s.get("s3_url")]
    
    if not students_with_pdfs:
        return {
            "success": True,
            "status": "SKIPPED",
            "message": f"No PDFs available for WhatsApp sending in batch {batch_name}",
            "sent": 0,
            "failed": 0,
            "skipped": len(students),
            "time": time.time() - start_time
        }
    
    print(f"  Sending WhatsApp messages to {len(students_with_pdfs)} students...")
    
    # Send WhatsApp messages
    whatsapp_results = send_batch_whatsapp_messages(students_with_pdfs, report_type, location, batch_name, period_id)
    
    # Calculate statistics
    sent_count = sum(1 for r in whatsapp_results if r.get("success") and r.get("status") == "SENT")
    failed_count = sum(1 for r in whatsapp_results if not r.get("success") or r.get("status") == "FAILED")
    skipped_count = sum(1 for r in whatsapp_results if r.get("status") == "SKIPPED")
    
    # Update students with basic WhatsApp status in parent_whatapp_report
    for student in students:
        if student.get("s3_url"):
            whatsapp_result = next((r for r in whatsapp_results if r.get("student_id") == student.get("id")), None)
            if whatsapp_result:
                student["whatsapp_status"] = whatsapp_result.get("status")
                student["whatsapp_error"] = whatsapp_result.get("error")
    
    # Update parent_whatapp_report with basic WhatsApp status
    db["parent_whatapp_report"].update_one(
        {"period_id": period_id, "report_type": report_type},
        {"$set": {f"locations.{location}.{batch_name}": students}}
    )
    
    processing_time = time.time() - start_time
    
    return {
        "success": True,
        "status": "COMPLETED",
        "message": f"WhatsApp sent to {sent_count} students, {failed_count} failed, {skipped_count} skipped",
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "time": processing_time
    }


def get_batches_ready_for_whatsapp(period_id: str, report_type: str) -> list:
    """Get batches that have completed PDF processing and are ready for WhatsApp"""
    # Get current status from tracker
    from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker
    tracker = ReportStatusTracker(report_type, period_id)
    status = tracker.get_status()
    
    if not status:
        return []
    
    ready_batches = []
    locations = status.get("locations", {})
    
    for location_name, location_data in locations.items():
        pdf_status = location_data.get("pdf", {}).get("status")
        batches = location_data.get("batches", {})
        
        # Only process if location PDF processing is completed
        if pdf_status == "COMPLETED":
            for batch_name, batch_data in batches.items():
                batch_pdf_status = batch_data.get("pdf", {}).get("status")
                batch_whatsapp_status = batch_data.get("whatsapp", {}).get("status", "PENDING")
                
                # Ready if PDF is completed but WhatsApp is still pending (not COMPLETED or PROCESSING)
                if batch_pdf_status == "COMPLETED" and batch_whatsapp_status not in ["COMPLETED", "PROCESSING"]:
                    ready_batches.append({
                        "location": location_name,
                        "batch_name": batch_name,
                        "pdf_students": batch_data.get("pdf", {}).get("success", 0)
                    })
    
    return ready_batches


def process_whatsapp_reports(report_type, period_id, location=None, batch=None):
    """
    Main WhatsApp processing function for different scenarios
    
    Args:
        report_type: Type of report (weekly/monthly)
        period_id: Period ID for the report
        location: Optional location filter
        batch: Optional specific batch
    """
    import time
    start_time = time.time()
    
    # Initialize tracker
    tracker = ReportStatusTracker(report_type, period_id)
    
    # Case 3: Specific batch
    if location and batch:
        print(f"Sending WhatsApp for specific batch: {batch} in {location}")
        
        # Check if WhatsApp already completed for this batch
        status = tracker.get_status()
        if status:
            # Case 3: Check global_status AND location_status AND batch_status
            global_whatsapp_status = status.get("global_whatsapp", {}).get("status")
            location_whatsapp_status = status.get("locations", {}).get(location, {}).get("whatsapp", {}).get("status")
            batch_whatsapp_status = status.get("locations", {}).get(location, {}).get("batches", {}).get(batch, {}).get("whatsapp", {}).get("status")
            
            # Only check batch-specific status for Case 3
            if batch_whatsapp_status == "COMPLETED":
                batch_whatsapp = status.get("locations", {}).get(location, {}).get("batches", {}).get(batch, {}).get("whatsapp", {})
                return {
                    "success": True,
                    "message": f"WhatsApp already sent for batch {batch} in {location}",
                    "summary": {
                        "total_batches": 1, 
                        "sent": batch_whatsapp.get("sent", 0), 
                        "failed": batch_whatsapp.get("failed", 0), 
                        "skipped": batch_whatsapp.get("skipped", 0)
                    },
                    "results": [{
                        "success": True,
                        "status": "SKIPPED",
                        "message": f"WhatsApp already sent for batch {batch}",
                        "sent": batch_whatsapp.get("sent", 0), 
                        "failed": batch_whatsapp.get("failed", 0), 
                        "skipped": batch_whatsapp.get("skipped", 0), 
                        "time": 0
                    }]
                }
        
        # Initialize WhatsApp processing status only if not completed
        current_status = tracker.get_status() or {}
        global_whatsapp_status = current_status.get("global_whatsapp", {}).get("status")
        if global_whatsapp_status != "COMPLETED":
            tracker.update_global_status(
                whatsapp_stats=create_stats_object(
                    status="PROCESSING",
                    sent=0, failed=0, skipped=0,
                    message="WhatsApp processing started"
                )
            )
        
        # Initialize location WhatsApp status to PROCESSING only if not completed
        location_whatsapp_status = current_status.get("locations", {}).get(location, {}).get("whatsapp", {}).get("status")
        if location_whatsapp_status != "COMPLETED":
            tracker.update_location_status(location, whatsapp_stats=create_stats_object(
                status="PROCESSING",
                sent=0, failed=0, skipped=0,
                message=f"Processing WhatsApp for {location}"
            ))
        
        result = process_whatsapp_for_batch(location, batch, period_id, report_type, tracker)
        
        # Update tracker with WhatsApp stats (parent_report_status - for counts/completion only)
        whatsapp_stats = create_stats_object(
            status=result.get("status"),
            sent=result.get("sent", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            time_s=result.get("time", 0),
            message=result.get("message", "")
        )
        
        tracker.update_batch_status(location, batch, whatsapp_stats=whatsapp_stats)
        tracker.update_location_status(location, whatsapp_stats=whatsapp_stats)
        
        # Update location status to COMPLETED
        location_whatsapp_stats = create_stats_object(
            status="COMPLETED",
            sent=result.get("sent", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            time_s=result.get("time", 0),
            message=f"WhatsApp completed for {location}"
        )
        tracker.update_location_status(location, whatsapp_stats=location_whatsapp_stats)
        
        # Update global counters
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import create_batch_stats_object
        batch_stats = create_batch_stats_object(
            status="COMPLETED",
            whatsapp_completed=1,
            message="WhatsApp completed for batch"
        )
        location_stats = {
            "whatsapp_completed": 1,
            "status": "COMPLETED",
            "message": f"WhatsApp completed for {location}"
        }
        
        # Update global WhatsApp with actual values
        global_whatsapp_stats = create_stats_object(
            status="COMPLETED",
            sent=result.get("sent", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            time_s=result.get("time", 0),
            message=f"WhatsApp completed: {result.get('sent', 0)} sent, {result.get('failed', 0)} failed"
        )
        
        tracker.update_global_status(
            whatsapp_stats=global_whatsapp_stats,
            batch_stats=batch_stats,
            location_stats=location_stats
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "summary": {
                "total_batches": 1,
                "sent": result.get("sent", 0),
                "failed": result.get("failed", 0),
                "skipped": result.get("skipped", 0)
            },
            "results": [result]
        }
    
    # Case 2: All batches in specific location
    elif location:
        print(f"Sending WhatsApp for all ready batches in location: {location}")
        
        # Check if location WhatsApp already completed
        status = tracker.get_status()
        if status:
            # Case 2: Check global_status AND location_status
            global_whatsapp_status = status.get("global_whatsapp", {}).get("status")
            location_whatsapp_status = status.get("locations", {}).get(location, {}).get("whatsapp", {}).get("status")
            
            # Only check location-specific status for Case 2
            if location_whatsapp_status == "COMPLETED":
                location_whatsapp = status.get("locations", {}).get(location, {}).get("whatsapp", {})
                return {
                    "success": True,
                    "message": f"WhatsApp already completed for location {location}",
                    "summary": {
                        "total_batches": 0, 
                        "sent": location_whatsapp.get("sent", 0), 
                        "failed": location_whatsapp.get("failed", 0), 
                        "skipped": location_whatsapp.get("skipped", 0)
                    },
                    "results": []
                }
        
        # Initialize WhatsApp processing status only if not completed
        current_status = tracker.get_status() or {}
        global_whatsapp_status = current_status.get("global_whatsapp", {}).get("status")
        if global_whatsapp_status != "COMPLETED":
            tracker.update_global_status(
                whatsapp_stats=create_stats_object(
                    status="PROCESSING",
                    sent=0, failed=0, skipped=0,
                    message="WhatsApp processing started"
                )
            )
        
        # Initialize location WhatsApp status to PROCESSING only if not completed
        location_whatsapp_status = current_status.get("locations", {}).get(location, {}).get("whatsapp", {}).get("status")
        if location_whatsapp_status != "COMPLETED":
            tracker.update_location_status(location, whatsapp_stats=create_stats_object(
                status="PROCESSING",
                sent=0, failed=0, skipped=0,
                message=f"Processing WhatsApp for {location}"
            ))
        
        # Get ready batches for this location
        all_ready_batches = get_batches_ready_for_whatsapp(period_id, report_type)
        location_batches = [b for b in all_ready_batches if b["location"] == location]
        
        if not location_batches:
            return {
                "success": False,
                "message": f"No batches ready for WhatsApp in {location}",
                "summary": {"total_batches": 0, "sent": 0, "failed": 0, "skipped": 0},
                "results": []
            }
        
        results = []
        total_sent = total_failed = total_skipped = 0
        
        for batch_info in location_batches:
            result = process_whatsapp_for_batch(
                batch_info["location"], 
                batch_info["batch_name"], 
                period_id, 
                report_type, 
                tracker
            )
            results.append(result)
            total_sent += result.get("sent", 0)
            total_failed += result.get("failed", 0)
            total_skipped += result.get("skipped", 0)
            
            # Update batch and location status for each batch
            whatsapp_stats = create_stats_object(
                status=result.get("status"),
                sent=result.get("sent", 0),
                failed=result.get("failed", 0),
                skipped=result.get("skipped", 0),
                time_s=result.get("time", 0),
                message=result.get("message", "")
            )
            tracker.update_batch_status(batch_info["location"], batch_info["batch_name"], whatsapp_stats=whatsapp_stats)
            tracker.update_location_status(batch_info["location"], whatsapp_stats=whatsapp_stats)
        
        # Update location status to COMPLETED after all batches done
        location_whatsapp_stats = create_stats_object(
            status="COMPLETED",
            sent=total_sent,
            failed=total_failed,
            skipped=total_skipped,
            time_s=time.time() - start_time,
            message=f"WhatsApp completed for {location}: {total_sent} sent, {total_failed} failed"
        )
        # Set final location status to COMPLETED
        tracker.collection.update_one(
            {"_id": tracker.doc_id},
            {"$set": {
                f"locations.{location}.whatsapp.status": "COMPLETED",
                f"locations.{location}.whatsapp.message": location_whatsapp_stats["message"]
            }},
            upsert=True
        )
        
        # Update global counters for location completion
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import create_batch_stats_object
        batch_stats = create_batch_stats_object(
            status="COMPLETED",
            whatsapp_completed=len(location_batches),
            message=f"WhatsApp completed for {len(location_batches)} batches"
        )
        location_stats = {
            "whatsapp_completed": 1,
            "status": "COMPLETED",
            "message": f"WhatsApp completed for {location}"
        }
        
        # Update global WhatsApp with cumulative values
        global_whatsapp_stats = create_stats_object(
            status="COMPLETED",
            sent=total_sent,
            failed=total_failed,
            skipped=total_skipped,
            time_s=time.time() - start_time,
            message=f"WhatsApp completed for {location}: {total_sent} sent, {total_failed} failed"
        )
        
        tracker.update_global_status(
            whatsapp_stats=global_whatsapp_stats,
            batch_stats=batch_stats,
            location_stats=location_stats
        )
        
        return {
            "success": True,
            "message": f"Processed {len(location_batches)} batches in {location}: {total_sent} sent, {total_failed} failed, {total_skipped} skipped",
            "summary": {
                "total_batches": len(location_batches),
                "sent": total_sent,
                "failed": total_failed,
                "skipped": total_skipped
            },
            "results": results
        }
    
    # Case 1: All locations and batches
    else:
        print("Sending WhatsApp for all ready batches in all locations")
        
        # Check if global WhatsApp already completed
        status = tracker.get_status()
        if status:
            global_whatsapp_status = status.get("global_whatsapp", {}).get("status")
            if global_whatsapp_status == "COMPLETED":
                # Get actual counts from status
                global_whatsapp = status.get("global_whatsapp", {})
                return {
                    "success": True,
                    "message": "WhatsApp already completed for all locations",
                    "summary": {
                        "total_batches": 0, 
                        "sent": global_whatsapp.get("sent", 0), 
                        "failed": global_whatsapp.get("failed", 0), 
                        "skipped": global_whatsapp.get("skipped", 0)
                    },
                    "results": []
                }
        
        # Initialize WhatsApp processing status only if not completed
        current_status = tracker.get_status() or {}
        global_whatsapp_status = current_status.get("global_whatsapp", {}).get("status")
        if global_whatsapp_status != "COMPLETED":
            tracker.update_global_status(
                whatsapp_stats=create_stats_object(
                    status="PROCESSING",
                    sent=0, failed=0, skipped=0,
                    message="WhatsApp processing started"
                )
            )
        
        ready_batches = get_batches_ready_for_whatsapp(period_id, report_type)
        
        if not ready_batches:
            return {
                "success": False,
                "message": "No batches ready for WhatsApp sending",
                "summary": {"total_batches": 0, "sent": 0, "failed": 0, "skipped": 0},
                "results": []
            }
        
        # Group by location for sequential processing
        locations = list(set(b["location"] for b in ready_batches))
        print(f"Found {len(ready_batches)} ready batches across {len(locations)} locations")
        
        all_results = []
        total_sent = total_failed = total_skipped = 0
        
        # Process each location sequentially
        for current_location in locations:
            print(f"\n--- Sending WhatsApp for Location: {current_location} ---")
            location_batches = [b for b in ready_batches if b["location"] == current_location]
            
            # Check if this location WhatsApp already completed
            location_whatsapp_status = status.get("locations", {}).get(current_location, {}).get("whatsapp", {}).get("status") if status else None
            if location_whatsapp_status == "COMPLETED":
                print(f"WhatsApp already completed for {current_location}, skipping...")
                continue
            
            # Initialize location WhatsApp status to PROCESSING only if not completed
            current_status = tracker.get_status() or {}
            location_whatsapp_status = current_status.get("locations", {}).get(current_location, {}).get("whatsapp", {}).get("status")
            if location_whatsapp_status != "COMPLETED":
                tracker.update_location_status(current_location, whatsapp_stats=create_stats_object(
                    status="PROCESSING",
                    sent=0, failed=0, skipped=0,
                    message=f"Processing WhatsApp for {current_location}"
                ))
            
            for batch_info in location_batches:
                result = process_whatsapp_for_batch(
                    batch_info["location"], 
                    batch_info["batch_name"], 
                    period_id, 
                    report_type, 
                    tracker
                )
                all_results.append(result)
                total_sent += result.get("sent", 0)
                total_failed += result.get("failed", 0)
                total_skipped += result.get("skipped", 0)
                
                # Update batch status for each batch
                whatsapp_stats = create_stats_object(
                    status=result.get("status"),
                    sent=result.get("sent", 0),
                    failed=result.get("failed", 0),
                    skipped=result.get("skipped", 0),
                    time_s=result.get("time", 0),
                    message=result.get("message", "")
                )
                tracker.update_batch_status(batch_info["location"], batch_info["batch_name"], whatsapp_stats=whatsapp_stats)
                tracker.update_location_status(batch_info["location"], whatsapp_stats=whatsapp_stats)
            
            # Update location status after completing all batches in location
            # Get results for this specific location
            location_results = [r for r in all_results[-len(location_batches):]]
            location_sent = sum(r.get("sent", 0) for r in location_results)
            location_failed = sum(r.get("failed", 0) for r in location_results)
            location_skipped = sum(r.get("skipped", 0) for r in location_results)
            
            location_whatsapp_stats = create_stats_object(
                status="COMPLETED",
                sent=location_sent,
                failed=location_failed,
                skipped=location_skipped,
                time_s=0,
                message=f"WhatsApp completed for {current_location}: {location_sent} sent, {location_failed} failed"
            )
            # Set final location status to COMPLETED
            tracker.collection.update_one(
                {"_id": tracker.doc_id},
                {"$set": {
                    f"locations.{current_location}.whatsapp.status": "COMPLETED",
                    f"locations.{current_location}.whatsapp.message": location_whatsapp_stats["message"]
                }},
                upsert=True
            )
            
            # Update global location counter for this location
            location_stats = {
                "whatsapp_completed": 1,
                "status": "PROCESSING",
                "message": f"Completed WhatsApp for {current_location}"
            }
            tracker.update_global_status(location_stats=location_stats)
            
            print(f"Completed {current_location}: {len(location_batches)} batches processed")
        
        # Update final global WhatsApp status
        global_whatsapp_stats = create_stats_object(
            status="COMPLETED",
            sent=total_sent,
            failed=total_failed,
            skipped=total_skipped,
            time_s=time.time() - start_time,
            message=f"WhatsApp completed: {total_sent} sent, {total_failed} failed, {total_skipped} skipped"
        )
        # Update final global counters
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import create_batch_stats_object
        final_batch_stats = create_batch_stats_object(
            status="COMPLETED",
            whatsapp_completed=len(ready_batches),
            message=f"WhatsApp completed for {len(ready_batches)} batches across {len(locations)} locations"
        )
        final_location_stats = {
            "status": "COMPLETED",
            "message": f"WhatsApp completed for all {len(locations)} locations"
        }
        
        tracker.update_global_status(
            whatsapp_stats=global_whatsapp_stats,
            batch_stats=final_batch_stats,
            location_stats=final_location_stats
        )
        
        return {
            "success": True,
            "message": f"Processed {len(ready_batches)} batches across {len(locations)} locations: {total_sent} sent, {total_failed} failed, {total_skipped} skipped",
            "summary": {
                "total_batches": len(ready_batches),
                "sent": total_sent,
                "failed": total_failed,
                "skipped": total_skipped
            },
            "results": all_results
        }
