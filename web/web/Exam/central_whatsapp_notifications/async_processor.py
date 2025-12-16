import threading
import queue
import time
import logging
from web.Exam.central_whatsapp_notifications.log_records import SP_Weekly_Report, Daily_Exam_Notify
from web.Exam.central_whatsapp_notifications.wa_collections import wa_parent_collection, wa_examiner_collection
from web.Exam.central_whatsapp_notifications.helpers import extract_required

logger = logging.getLogger(__name__)

class AsyncWebhookProcessor:
    def __init__(self, num_workers=4, batch_size=50, batch_timeout=2):
        self.parent_queue = queue.Queue(maxsize=100000)
        self.exam_queue = queue.Queue(maxsize=100000)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.running = True
        self.threads = []
        
        # Initialize processors
        self.parent_processor = SP_Weekly_Report(wa_parent_collection)
        self.exam_processor = Daily_Exam_Notify(wa_examiner_collection)
        
        # Start worker threads
        for i in range(num_workers):
            parent_thread = threading.Thread(target=self._process_parent_updates, daemon=True)
            exam_thread = threading.Thread(target=self._process_exam_updates, daemon=True)
            parent_thread.start()
            exam_thread.start()
            self.threads.extend([parent_thread, exam_thread])
    
    def queue_parent_update(self, payload):
        """Queue parent status update for async processing"""
        try:
            self.parent_queue.put_nowait(payload)
            return True
        except queue.Full:
            logger.error(f"Parent queue full: {self.parent_queue.qsize()}/{self.parent_queue.maxsize} - dropping request")
            return False
    
    def queue_exam_update(self, payload):
        """Queue exam status update for async processing"""
        try:
            self.exam_queue.put_nowait(payload)
            return True
        except queue.Full:
            logger.warning("Exam queue full, dropping request")
            return False
    
    def _process_updates(self, queue_obj, batch_processor, error_msg):
        """Common batch processing logic"""
        batch = []
        last_process_time = time.time()
        
        while self.running:
            try:
                # Get item with timeout
                try:
                    item = queue_obj.get(timeout=0.5)
                    batch.append(item)
                except queue.Empty:
                    pass
                
                # Process batch if size reached or timeout
                current_time = time.time()
                if (len(batch) >= self.batch_size or 
                    (batch and current_time - last_process_time >= self.batch_timeout)):
                    
                    batch_processor(batch)
                    batch = []
                    last_process_time = current_time
                    
            except Exception as e:
                logger.error(f"{error_msg}: {e}")
                batch = []  # Clear batch on error
    
    def _process_parent_updates(self):
        """Process parent updates in batches"""
        self._process_updates(self.parent_queue, self._process_parent_batch, "Error in parent processor")
    
    def _process_exam_updates(self):
        """Process exam updates in batches"""
        self._process_updates(self.exam_queue, self._process_exam_batch, "Error in exam processor")
    
    def _process_parent_batch(self, batch):
        """Process batch of parent updates"""
        for payload in batch:
            try:
                info = extract_required(payload)
                print(info)
                record_id = info.get("id")
                batch_name = info.get("batch")
                period_id = info.get("period_id") or info.get("weekId")
                location = info.get("location")
                report_type = info.get("report_type", "weekly")
                
                if record_id and batch_name and period_id:

                    print("=== Processing Parent Update ===","==="*10)
                    self.parent_processor.update_interaction_fields(
                        period_id, location, batch_name, record_id, info, report_type
                    )
            except Exception as e:
                logger.error(f"Failed to process parent update: {e}")
    
    def _process_exam_batch(self, batch):
        """Process batch of exam updates"""
        for payload in batch:
            try:
                info = extract_required(payload, purpose="Daily_Exam")
                record_id = info.get("id")
                batch_name = info.get("batch")
                date = info.get("date")
                
                if record_id and batch_name and date:
                    self.exam_processor.update_interaction_fields(
                        date, batch_name, record_id, info
                    )
            except Exception as e:
                logger.error(f"Failed to process exam update: {e}")
    
    def shutdown(self):
        """Gracefully shutdown the processor"""
        self.running = False
        for thread in self.threads:
            thread.join(timeout=5)

# Global processor instance
webhook_processor = AsyncWebhookProcessor()