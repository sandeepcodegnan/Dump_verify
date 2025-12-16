"""WhatsApp Client - External Service Integration (SoC)"""
import time
import threading
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
from web.Exam.Daily_Exam.config.settings import WhatsAppConfig
from web.Exam.central_whatsapp_notifications.payloads import Examiner_Payload, clean_phone
from web.Exam.central_whatsapp_notifications.wa_send import send_whatsapp
from web.Exam.exam_central_db import student_collection

class WhatsAppClient:
    """External service client for WhatsApp notifications"""
    
    def __init__(self):
        # Configurable rate limiting from centralized config
        self.max_workers = WhatsAppConfig.MAX_WORKERS
        self.rate_limit_delay = WhatsAppConfig.RATE_LIMIT_SECONDS
        
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="WhatsApp-")
        self._rate_limit_lock = threading.Lock()
        self._last_send_time = 0
    
    def send_exam_notifications(self, exam_data: Dict) -> Dict:
        """Send exam notifications asynchronously - fetches student data from DB"""
        
        def notify_student(student_id: str):
            """Send notification to single student with rate limiting"""
            try:
                # Fetch student data from database
                stu = student_collection.find_one({"id": student_id})
                if not stu:
                    return {"status": "error", "student_id": student_id, "error": "student_not_found"}
                
                if stu.get("placed") == True:
                    return {"status": "skipped", "reason": "placed"}
                
                name = stu.get("name")
                phone = clean_phone(stu.get("studentPhNumber", ""))
                
                if not (name and phone):
                    return {"status": "skipped", "reason": "missing_data"}
                
                # Rate limiting: configurable delay between sends
                with self._rate_limit_lock:
                    current_time = time.time()
                    time_since_last = current_time - self._last_send_time
                    if time_since_last < self.rate_limit_delay:
                        time.sleep(self.rate_limit_delay - time_since_last)
                    self._last_send_time = time.time()
                
                subs = ", ".join(s["subject"] for s in exam_data.get("subjects", []))
                
                # Window-aware notification format
                window_start = exam_data.get("windowStart", "N/A")
                window_end = exam_data.get("windowEnd", "N/A")
                window_period = f"{window_start}-{window_end}"
                
                exam_payload = Examiner_Payload(
                    name, student_id, phone, exam_data["examName"],
                    exam_data["startDate"], window_period, 
                    exam_data["totalExamTime"], subs, exam_data["batch"]
                )
                
                status = {k: v for k, v in stu.items() if k in ("id", "BatchNo")}
                status['date'] = exam_data["startDate"]
                status['studentPhNumber'] = phone
                status['examType'] = exam_data.get("examType", "Daily-Exam")
                
                success = send_whatsapp(exam_payload, status, "Daily_Exam")
                return {"status": "sent" if success else "failed", "student_id": student_id}
                
            except Exception as e:
                return {"status": "error", "student_id": student_id, "error": str(e)}
        
        # Get student IDs from exam data
        student_ids = exam_data.get("studentIds", [])
        if not student_ids:
            return {"status": "error", "error": "no_student_ids"}
        
        # Submit all tasks asynchronously - don't wait for completion
        futures = []
        for student_id in student_ids:
            future = self.executor.submit(notify_student, student_id)
            futures.append(future)
        
        # Return immediately with queued count
        return {
            "total_students": len(student_ids),
            "queued": len(futures),
            "exam_name": exam_data.get("examName", ""),
            "status": "queued_async"
        }
    
    def __del__(self):
        """Cleanup thread pool on destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)