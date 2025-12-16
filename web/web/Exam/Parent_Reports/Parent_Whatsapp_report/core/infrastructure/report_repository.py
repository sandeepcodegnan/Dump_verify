class ReportRepository:
    def __init__(self, db):
        self.db = db

    def get_active_batches(self, location=None, batch_name=None):
        query = {"Status": "Active"}
        if location:
            query["location"] = location
        if batch_name:
            query["Batch"] = batch_name
        batches = list(self.db["Batches"].find(query, {"Batch": 1, "location": 1, "_id": 0}))
        filtered = []
        for b in batches:
            n = (b.get("Batch") or "").lower()
            if "dropout" not in n and "s4" not in n:
                filtered.append(b)
        return filtered

    def get_active_locations(self):
        return list(self.db["Batches"].distinct("location", {
            "Status": "Active",
            "Batch": {"$not": {"$regex": "dropout|s4", "$options": "i"}}
        }))
