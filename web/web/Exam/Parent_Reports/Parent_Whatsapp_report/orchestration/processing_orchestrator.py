from concurrent.futures import ThreadPoolExecutor, as_completed
from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.tracker_manager import TrackerManager


class ProcessingOrchestrator:
    def __init__(self, report_type, force=False, batch_processor=None):
        self.report_type = report_type
        self.force = force
        self.batch_processor = batch_processor
    
    def process_location_batches(self, batches, period_id, start_date, end_date, tracker):
        import os
        import psutil
        
        cpu_count = os.cpu_count() or 4
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        base_batch_workers = min(cpu_count * 2, 16)
        memory_batch_limit = int(memory_gb / 2)
        workload_batch_limit = min(len(batches), 12)
        max_batch_workers = min(base_batch_workers, memory_batch_limit, workload_batch_limit)
        
        print(f"  Using {max_batch_workers} workers for {len(batches)} batches")
        
        if self.batch_processor is None:
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.services.report_processing_service import process_single_batch_wrapper
            self.batch_processor = process_single_batch_wrapper
        batch_args = [
            (batch_info, self.report_type, self.force, period_id, start_date, end_date)
            for batch_info in batches
        ]
        
        location_results = []
        
        with ThreadPoolExecutor(max_workers=max_batch_workers) as executor:
            future_to_batch = {
                executor.submit(self.batch_processor, args): args[0]
                for args in batch_args
            }
            
            for future in as_completed(future_to_batch):
                batch_info = future_to_batch[future]
                try:
                    result = future.result()
                    location_results.append(result)
                    self._update_batch_status(result, batch_info, tracker)
                except Exception as e:
                    from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.error_handler import ErrorHandler
                    error_result = ErrorHandler.handle_batch_error(e, batch_info, tracker)
                    location_results.append(error_result)
                    self._update_batch_status(error_result, batch_info, tracker)
        
        return location_results
    
    def _update_batch_status(self, result, batch_info, tracker):
        status = result.get("status", "UNKNOWN")
        batch_name = batch_info.get("Batch", "Unknown")
        location_name = batch_info.get("location", "Unknown")
        students_processed = result.get("processed", 0)
        
        print(f"  Completed: {batch_name} - {status} ({students_processed} students)")
        
        pdf_stats = TrackerManager.create_pdf_stats_from_result(result)
        batch_stats = TrackerManager.create_batch_stats_from_result(result)
        
        tracker.update_batch_status(location_name, batch_name, pdf_stats=pdf_stats)
        tracker.update_location_status(location_name, pdf_stats=pdf_stats, batch_stats=batch_stats)
