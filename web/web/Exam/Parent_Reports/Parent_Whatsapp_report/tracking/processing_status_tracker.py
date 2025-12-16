from datetime import datetime
from web.Exam.exam_central_db import db


class ReportStatusTracker:
    def __init__(self, report_type, period_id):
        self.report_type = report_type
        self.period_id = period_id
        self.doc_id = f"{report_type}_{period_id}"
        self.collection = db["parent_report_status"]
        
    def initialize_status(self):
        existing_doc = self.collection.find_one({"_id": self.doc_id})
        if existing_doc:
            self.collection.update_one({"_id": self.doc_id}, {"$set": {"last_updated": datetime.utcnow()}})
            return existing_doc
        doc = {
            "_id": self.doc_id,
            "report_type": self.report_type,
            "period_id": self.period_id,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "timeline": [],
            "errors": [],
            "global_pdf": {"status": "PENDING", "success": 0, "error": 0, "skipped": 0, "time_s": 0.0, "message": ""},
            "global_batches": {"status": "PENDING", "total": 0, "pdf_completed": 0, "whatsapp_completed": 0, "skipped": 0, "time_s": 0.0, "message": ""},
            "global_locations": {"status": "PENDING", "total": 0, "pdf_completed": 0, "whatsapp_completed": 0, "processing": 0, "time_s": 0.0, "message": ""},
            "global_whatsapp": {"status": "PENDING", "sent": 0, "failed": 0, "skipped": 0, "time_s": 0.0, "message": ""},
            "locations": {}
        }
        self.collection.insert_one(doc)
        return doc
    
    def add_timeline_event(self, event, details=None):
        timeline_entry = {"timestamp": datetime.utcnow(), "event": event, "details": details or {}}
        self.collection.update_one({"_id": self.doc_id}, {"$push": {"timeline": timeline_entry}, "$set": {"last_updated": datetime.utcnow()}})
    
    def add_error(self, error_msg, location=None, batch=None):
        error_entry = {"timestamp": datetime.utcnow(), "message": error_msg, "location": location, "batch": batch}
        self.collection.update_one({"_id": self.doc_id}, {"$push": {"errors": error_entry}, "$set": {"last_updated": datetime.utcnow()}})
    
    def update_location_status(self, location, pdf_stats=None, whatsapp_stats=None, batch_stats=None):
        update_operations = {"$set": {"last_updated": datetime.utcnow()}}
        if pdf_stats:
            self.collection.update_one({"_id": self.doc_id}, {"$setOnInsert": {
                f"locations.{location}.pdf.success": 0,
                f"locations.{location}.pdf.error": 0,
                f"locations.{location}.pdf.skipped": 0,
                f"locations.{location}.pdf.time_s": 0.0,
                f"locations.{location}.pdf.status": "PENDING",
                f"locations.{location}.pdf.message": ""
            }}, upsert=True)
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                f"locations.{location}.pdf.success": pdf_stats.get("success", 0),
                f"locations.{location}.pdf.error": pdf_stats.get("error", 0),
                f"locations.{location}.pdf.skipped": pdf_stats.get("skipped", 0),
                f"locations.{location}.pdf.time_s": pdf_stats.get("time_s", 0.0)
            })
            current_doc = self.collection.find_one({"_id": self.doc_id}) or {}
            current_location = current_doc.get("locations", {}).get(location, {})
            current_pdf = current_location.get("pdf", {})
            current_success = current_pdf.get("success", 0)
            new_total_success = current_success + pdf_stats.get("success", 0)
            location_message = f"Processed {new_total_success} students in {location}"
            update_operations["$set"].update({f"locations.{location}.pdf.message": location_message})
        if whatsapp_stats:
            self.collection.update_one({"_id": self.doc_id}, {"$setOnInsert": {
                f"locations.{location}.whatsapp.sent": 0,
                f"locations.{location}.whatsapp.failed": 0,
                f"locations.{location}.whatsapp.skipped": 0,
                f"locations.{location}.whatsapp.time_s": 0.0,
                f"locations.{location}.whatsapp.status": "PENDING",
                f"locations.{location}.whatsapp.message": ""
            }}, upsert=True)
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                f"locations.{location}.whatsapp.sent": whatsapp_stats.get("sent", 0),
                f"locations.{location}.whatsapp.failed": whatsapp_stats.get("failed", 0),
                f"locations.{location}.whatsapp.skipped": whatsapp_stats.get("skipped", 0),
                f"locations.{location}.whatsapp.time_s": whatsapp_stats.get("time_s", 0.0)
            })
            update_operations["$set"].update({
                f"locations.{location}.whatsapp.status": whatsapp_stats.get("status", "PENDING"),
                f"locations.{location}.whatsapp.message": whatsapp_stats.get("message", "")
            })
        if batch_stats:
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                f"locations.{location}.batches_count.total": batch_stats.get("total", 0),
                f"locations.{location}.batches_count.pdf_completed": batch_stats.get("pdf_completed", 0),
                f"locations.{location}.batches_count.skipped": batch_stats.get("skipped", 0),
                f"locations.{location}.batches_count.time_s": batch_stats.get("time_s", 0.0)
            })
            update_operations["$set"].update({f"locations.{location}.batches_count.message": batch_stats.get("message", "")})
        self.collection.update_one({"_id": self.doc_id}, update_operations, upsert=True)
    
    def update_batch_status(self, location, batch_name, pdf_stats=None, whatsapp_stats=None):
        update_doc = {"last_updated": datetime.utcnow()}
        if pdf_stats:
            update_doc[f"locations.{location}.batches.{batch_name}.pdf"] = pdf_stats
        if whatsapp_stats:
            update_doc[f"locations.{location}.batches.{batch_name}.whatsapp"] = whatsapp_stats
        self.collection.update_one({"_id": self.doc_id}, {"$set": update_doc}, upsert=True)
    
    def update_global_status(self, pdf_stats=None, whatsapp_stats=None, batch_stats=None, location_stats=None):
        update_operations = {"$set": {"last_updated": datetime.utcnow()}}
        if pdf_stats:
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                "global_pdf.success": pdf_stats.get("success", 0),
                "global_pdf.error": pdf_stats.get("error", 0),
                "global_pdf.skipped": pdf_stats.get("skipped", 0),
                "global_pdf.time_s": pdf_stats.get("time_s", 0.0)
            })
            global_status = pdf_stats.get("status", "COMPLETED")
            update_operations["$set"].update({"global_pdf.status": global_status, "global_pdf.message": pdf_stats.get("message", "")})
        if whatsapp_stats:
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                "global_whatsapp.sent": whatsapp_stats.get("sent", 0),
                "global_whatsapp.failed": whatsapp_stats.get("failed", 0),
                "global_whatsapp.skipped": whatsapp_stats.get("skipped", 0),
                "global_whatsapp.time_s": whatsapp_stats.get("time_s", 0.0)
            })
            update_operations["$set"].update({"global_whatsapp.status": whatsapp_stats.get("status", "PENDING"), "global_whatsapp.message": whatsapp_stats.get("message", "")})
        if batch_stats:
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            if batch_stats.get("total", 0) > 0:
                update_operations["$inc"]["global_batches.total"] = batch_stats.get("total", 0)
            update_operations["$inc"].update({
                "global_batches.pdf_completed": batch_stats.get("pdf_completed", 0),
                "global_batches.whatsapp_completed": batch_stats.get("whatsapp_completed", 0),
                "global_batches.skipped": batch_stats.get("skipped", 0),
                "global_batches.time_s": batch_stats.get("time_s", 0.0)
            })
            update_operations["$set"].update({"global_batches.status": batch_stats.get("status", "COMPLETED"), "global_batches.message": batch_stats.get("message", "")})
        if location_stats:
            if "$inc" not in update_operations:
                update_operations["$inc"] = {}
            update_operations["$inc"].update({
                "global_locations.total": location_stats.get("total", 0),
                "global_locations.pdf_completed": location_stats.get("pdf_completed", 0),
                "global_locations.whatsapp_completed": location_stats.get("whatsapp_completed", 0),
                "global_locations.processing": location_stats.get("processing", 0),
                "global_locations.time_s": location_stats.get("time_s", 0.0)
            })
            update_operations["$set"].update({"global_locations.status": location_stats.get("status", "COMPLETED"), "global_locations.message": location_stats.get("message", "")})
        self.collection.update_one({"_id": self.doc_id}, update_operations)
    
    def get_status(self):
        return self.collection.find_one({"_id": self.doc_id})


def create_stats_object(status, success=0, error=0, skipped=0, time_s=0.0, message="", **kwargs):
    stats = {"status": status, "success": success, "error": error, "skipped": skipped, "time_s": round(time_s, 2), "message": message}
    if "sent" in kwargs:
        stats["sent"] = kwargs["sent"]
        stats["success"] = kwargs["sent"]
    if "failed" in kwargs:
        stats["failed"] = kwargs["failed"]
        stats["error"] = kwargs["failed"]
    stats.update(kwargs)
    return stats


def create_batch_stats_object(status, total=0, pdf_completed=0, whatsapp_completed=0, skipped=0, time_s=0.0, message=""):
    return {"status": status, "total": total, "pdf_completed": pdf_completed, "whatsapp_completed": whatsapp_completed, "skipped": skipped, "time_s": round(time_s, 2), "message": message}
