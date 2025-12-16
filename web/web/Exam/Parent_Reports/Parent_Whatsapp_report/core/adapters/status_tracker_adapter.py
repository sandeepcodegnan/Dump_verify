class StatusTrackerAdapter:
    def __init__(self, tracker):
        self.tracker = tracker

    def set_location_pdf_completed(self, location):
        self.tracker.collection.update_one(
            {"_id": self.tracker.doc_id},
            {"$set": {
                f"locations.{location}.pdf.status": "COMPLETED",
                f"locations.{location}.batches_count.status": "COMPLETED"
            }},
            upsert=True
        )

    def set_location_whatsapp_completed(self, location, message=None):
        update = {
            f"locations.{location}.whatsapp.status": "COMPLETED"
        }
        if message:
            update[f"locations.{location}.whatsapp.message"] = message
        self.tracker.collection.update_one(
            {"_id": self.tracker.doc_id},
            {"$set": update},
            upsert=True
        )
