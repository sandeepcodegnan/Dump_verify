from datetime import datetime
from flask import current_app

def get_collections():
    try:
        if current_app:
            db = current_app.db
            return {
                'feature_flags': db['feature_flags'],
                'location_flags': db['feature_flags_location'],
                'batch_flags': db['feature_flags_batch']
            }
    except RuntimeError:
        pass
    
    from web.Exam.exam_central_db import feature_flags_collection, location_flags_collection, batch_flags_collection
    return {
        'feature_flags': feature_flags_collection,
        'location_flags': location_flags_collection,
        'batch_flags': batch_flags_collection
    }

def _load_flags() -> dict:
    collections = get_collections()
    return {doc["_id"]: doc.get("enabled", True) for doc in collections['feature_flags'].find()}

def _load_location_flags() -> dict:
    collections = get_collections()
    flags_by_location = {}
    for doc in collections['location_flags'].find():
        location = doc.get("location", "global")
        flag_name = doc.get("flag_name")
        enabled = doc.get("enabled", True)
        
        if location not in flags_by_location:
            flags_by_location[location] = {}
        
        flags_by_location[location][flag_name] = enabled
    
    return flags_by_location

def _load_batch_flags() -> dict:
    collections = get_collections()
    flags_by_batch = {}
    for doc in collections['batch_flags'].find():
        batch = doc.get("batch", "global")
        flag_name = doc.get("flag_name")
        enabled = doc.get("enabled", True)
        
        if batch not in flags_by_batch:
            flags_by_batch[batch] = {}
        
        if flag_name not in flags_by_batch[batch]:
            flags_by_batch[batch][flag_name] = enabled
    
    return flags_by_batch

def is_enabled(key: str, default: bool = False) -> bool:
    return _load_flags().get(key, default)

def is_enabled_for_location(flag_name: str, location: str, default: bool = False) -> bool:
    global_flag = is_enabled(flag_name)
    if not global_flag:
        return False
    
    flags_by_location = _load_location_flags()
    
    if location in flags_by_location and flag_name in flags_by_location[location]:
        return flags_by_location[location][flag_name]
    
    if "global" in flags_by_location and flag_name in flags_by_location["global"]:
        return flags_by_location["global"][flag_name]
    
    return default

def is_enabled_for_batch(flag_name: str, batch: str, location: str = None, default: bool = False) -> bool:
    global_flag = is_enabled(flag_name)
    if not global_flag:
        return False
    
    collections = get_collections()
    
    if location:
        batch_doc = collections['batch_flags'].find_one({"flag_name": flag_name, "batch": batch, "location": location})
        if batch_doc:
            location_flag = is_enabled_for_location(flag_name, location, None)
            if location_flag is False:
                return False
            return batch_doc.get("enabled", default)
    
    batch_doc = collections['batch_flags'].find_one({"flag_name": flag_name, "batch": batch})
    if batch_doc:
        if batch_doc.get("location"):
            location_flag = is_enabled_for_location(flag_name, batch_doc["location"], None)
            if location_flag is False:
                return False
        return batch_doc.get("enabled", default)
    
    global_batch_doc = collections['batch_flags'].find_one({"flag_name": flag_name, "batch": "global"})
    if global_batch_doc:
        return global_batch_doc.get("enabled", default)
    
    return default

def set_flag(key: str, enabled: bool):
    collections = get_collections()
    collections['feature_flags'].update_one(
        {"_id": key},
        {"$set": {"enabled": bool(enabled), "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    
def set_location_flag(flag_name: str, location: str, enabled: bool):
    collections = get_collections()
    collections['location_flags'].update_one(
        {"flag_name": flag_name, "location": location},
        {"$set": {"enabled": bool(enabled), "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    
def set_batch_flag(flag_name: str, batch: str, enabled: bool, location: str = None):
    collections = get_collections()
    update_data = {"enabled": bool(enabled), "updated_at": datetime.utcnow()}
    
    if location:
        update_data["location"] = location
        collections['batch_flags'].update_one(
            {"flag_name": flag_name, "batch": batch, "location": location},
            {"$set": update_data},
            upsert=True,
        )
    else:
        collections['batch_flags'].update_one(
            {"flag_name": flag_name, "batch": batch},
            {"$set": update_data},
            upsert=True,
        )

