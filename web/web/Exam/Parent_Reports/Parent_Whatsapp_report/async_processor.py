"""
Async processor for Parent WhatsApp Reports using threading
"""
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Optional
from web.Exam.Parent_Reports.Parent_Whatsapp_report.services.report_processing_service import process_reports


class AsyncTaskManager:
    """Manages async tasks with in-memory storage"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.tasks = {}
        return cls._instance
    
    def create_task(self, task_type: str, params: Dict) -> str:
        """Create new async task"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": task_type,
            "status": "QUEUED",
            "params": params,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Store in memory
        with self._lock:
            self.tasks[task_id] = task
        
        # Also store in status tracker timeline
        report_type = params.get("report_type")
        period_id = params.get("period_id")
        
        # Generate period_id if not provided
        if report_type and not period_id:
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
            start_date, end_date = get_report_config(report_type)["date_calculator"]()
            period_id = f"{start_date}_to_{end_date}"
            params["period_id"] = period_id
        
        if report_type and period_id:
            try:
                from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker
                tracker = ReportStatusTracker(report_type, period_id)
                tracker.add_timeline_event("ASYNC_TASK_CREATED", {
                    "task_id": task_id,
                    "task_type": task_type,
                    "params": params,
                    "status": "QUEUED"
                })
            except Exception as e:
                print(f"Failed to store task in timeline: {e}")
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID - check memory first, then timeline"""
        with self._lock:
            # Try memory first
            if task_id in self.tasks:
                return self.tasks[task_id].copy()
        
        # If not in memory, try to reconstruct from timeline
        return self._get_task_from_timeline(task_id)
    
    def _get_task_from_timeline(self, task_id: str) -> Optional[Dict]:
        """Reconstruct task from timeline events"""
        from web.Exam.exam_central_db import db
        
        # Find timeline events for this task
        timeline_docs = list(db["parent_report_status"].find({
            "timeline.details.task_id": task_id
        }, {"timeline": 1, "report_type": 1, "period_id": 1}))
        
        if not timeline_docs:
            return None
        
        # Reconstruct task from timeline events
        task = None
        for doc in timeline_docs:
            for event in doc.get("timeline", []):
                details = event.get("details", {})
                if details.get("task_id") == task_id:
                    if event["event"] == "ASYNC_TASK_CREATED":
                        task = {
                            "id": task_id,
                            "type": details.get("task_type"),
                            "status": details.get("status", "QUEUED"),
                            "params": details.get("params", {}),
                            "created_at": event["timestamp"],
                            "started_at": None,
                            "completed_at": None,
                            "result": None,
                            "error": None
                        }
                    elif event["event"] == "ASYNC_TASK_UPDATED" and task:
                        task["status"] = details.get("status", task["status"])
                        updates = details.get("updates", {})
                        if "started_at" in updates:
                            task["started_at"] = updates["started_at"]
                        if "completed_at" in updates:
                            task["completed_at"] = updates["completed_at"]
                        if "result" in updates:
                            task["result"] = updates["result"]
                        if "error" in updates:
                            task["error"] = updates["error"]
        
        return task
    
    def update_task(self, task_id: str, **updates):
        """Update task status"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(updates)
                
                # Also update in timeline if status changed
                if "status" in updates:
                    task = self.tasks[task_id]
                    params = task.get("params", {})
                    report_type = params.get("report_type")
                    period_id = params.get("period_id")
                    
                    if report_type and period_id:
                        try:
                            from web.Exam.Parent_Reports.Parent_Whatsapp_report.status_tracker import ReportStatusTracker
                            tracker = ReportStatusTracker(report_type, period_id)
                            tracker.add_timeline_event("ASYNC_TASK_UPDATED", {
                                "task_id": task_id,
                                "status": updates["status"],
                                "updates": updates
                            })
                        except Exception as e:
                            print(f"Failed to update task in timeline: {e}")


class AsyncReportProcessor:
    """Handles async report processing"""
    
    def __init__(self):
        self.task_manager = AsyncTaskManager()
    
    def start_processing(self, report_type: str, location: str = None, batch: str = None, 
                        force: bool = False, period_id: str = None, 
                        start_date: str = None, end_date: str = None) -> str:
        """Start async report processing"""
        
        # Generate period_id if not provided
        if not period_id:
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.config.report_config import get_report_config
            start_date, end_date = get_report_config(report_type)["date_calculator"]()
            period_id = f"{start_date}_to_{end_date}"
        
        # Create task
        params = {
            "report_type": report_type,
            "location": location,
            "batch": batch,
            "force": force,
            "period_id": period_id,
            "start_date": start_date,
            "end_date": end_date
        }
        
        task_id = self.task_manager.create_task("report_processing", params)
        
        # Start processing in background thread
        thread = threading.Thread(
            target=self._process_reports_async,
            args=(task_id,),
            daemon=True
        )
        thread.start()
        
        return task_id
    
    def _process_reports_async(self, task_id: str):
        """Background processing method"""
        try:
            # Update task status
            self.task_manager.update_task(
                task_id,
                status="PROCESSING",
                started_at=datetime.utcnow()
            )
            
            # Get task params
            task = self.task_manager.get_task(task_id)
            params = task["params"]
            
            # Process reports
            result = process_reports(
                report_type=params["report_type"],
                location=params["location"],
                batch=params["batch"],
                force=params["force"],
                period_id=params["period_id"],
                start_date=params["start_date"],
                end_date=params["end_date"]
            )
            
            # Update task with result
            self.task_manager.update_task(
                task_id,
                status="COMPLETED",
                completed_at=datetime.utcnow(),
                result=result
            )
            
        except Exception as e:
            # Update task with error
            self.task_manager.update_task(
                task_id,
                status="FAILED",
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    def start_whatsapp_processing(self, report_type: str, period_id: str, 
                                 location: str = None, batch: str = None) -> str:
        """Start async WhatsApp processing"""
        
        # Create task
        params = {
            "report_type": report_type,
            "period_id": period_id,
            "location": location,
            "batch": batch
        }
        
        task_id = self.task_manager.create_task("whatsapp_processing", params)
        
        # Start processing in background thread
        thread = threading.Thread(
            target=self._process_whatsapp_async,
            args=(task_id,),
            daemon=True
        )
        thread.start()
        
        return task_id
    
    def _process_whatsapp_async(self, task_id: str):
        """Background WhatsApp processing method"""
        try:
            # Update task status
            self.task_manager.update_task(
                task_id,
                status="PROCESSING",
                started_at=datetime.utcnow()
            )
            
            # Get task params
            task = self.task_manager.get_task(task_id)
            params = task["params"]
            
            # Process WhatsApp
            from web.Exam.Parent_Reports.Parent_Whatsapp_report.whatsapp.whatsapp_processor import process_whatsapp_reports
            result = process_whatsapp_reports(
                report_type=params["report_type"],
                period_id=params["period_id"],
                location=params["location"],
                batch=params["batch"]
            )
            
            # Update task with result
            self.task_manager.update_task(
                task_id,
                status="COMPLETED",
                completed_at=datetime.utcnow(),
                result=result
            )
            
        except Exception as e:
            # Update task with error
            self.task_manager.update_task(
                task_id,
                status="FAILED",
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get task status and result"""
        task = self.task_manager.get_task(task_id)
        
        if not task:
            return {"error": "Task not found"}
        
        # Calculate duration
        duration = None
        if task["started_at"]:
            end_time = task["completed_at"] or datetime.utcnow()
            duration = (end_time - task["started_at"]).total_seconds()
        
        return {
            "task_id": task["id"],
            "status": task["status"],
            "created_at": task["created_at"].isoformat(),
            "started_at": task["started_at"].isoformat() if task["started_at"] else None,
            "completed_at": task["completed_at"].isoformat() if task["completed_at"] else None,
            "duration_seconds": duration,
            "result": task["result"],
            "error": task["error"]
        }


# Singleton instance
async_processor = AsyncReportProcessor()
