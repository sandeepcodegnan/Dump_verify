from flask import request
from web.jwt.auth_middleware import Hierarchical_Feature_View
from flask_restful import Resource
from web.Exam.Flags.feature_flags import (
    is_enabled, set_flag, _load_flags,
    is_enabled_for_location, set_location_flag, _load_location_flags,
    is_enabled_for_batch, set_batch_flag, _load_batch_flags
)

# TODO: replace with your existing admin/JWT decorator
def admin_required(func):
    def wrapper(*args, **kwargs):
        # your real auth check goes here
        return func(*args, **kwargs)
    return wrapper

class FeatureToggle(Resource):
    """API for global feature flags."""
    @admin_required
    def get(self, key=None):
        if key:                                   # /flags/<key>
            return {"key": key, "enabled": is_enabled(key)}, 200
        return _load_flags(), 200                 # /flags  (all flags)

    @admin_required
    def post(self, key):
        body = request.get_json(force=True)
        if "enabled" not in body or not isinstance(body["enabled"], bool):
            return {"success": False,
                    "msg": "`enabled` boolean required."}, 400

        set_flag(key, body["enabled"])
        return {"success": True,
                "key": key,
                "enabled": is_enabled(key)}, 200

class LocationFeatureToggle(Resource):
    """API for location-based feature flags."""
    
    @admin_required
    def get(self, location=None, flag_name=None):
        if location and flag_name:                # /location-flags/<location>/<flag_name>
            return {
                "location": location,
                "flag_name": flag_name, 
                "enabled": is_enabled_for_location(flag_name, location)
            }, 200
        elif location:                            # /location-flags/<location>
            flags_by_location = _load_location_flags()
            location_flags = {}
            
            # Include location-specific flags
            if location in flags_by_location:
                location_flags.update(flags_by_location[location])
            
            # Include global flags that aren't overridden by location-specific ones
            if "global" in flags_by_location:
                for flag_name, enabled in flags_by_location["global"].items():
                    if flag_name not in location_flags:
                        location_flags[flag_name] = enabled
            
            return location_flags, 200
        else:                                     # /location-flags (all flags by location)
            return _load_location_flags(), 200

    @admin_required
    def post(self, location, flag_name):
        body = request.get_json(force=True)
        if "enabled" not in body or not isinstance(body["enabled"], bool):
            return {
                "success": False,
                "msg": "`enabled` boolean required."
            }, 400

        set_location_flag(flag_name, location, body["enabled"])
        return {
            "success": True,
            "location": location,
            "flag_name": flag_name,
            "enabled": is_enabled_for_location(flag_name, location)
        }, 200

class BatchFeatureToggle(Resource):
    """API for batch-based feature flags."""
    @admin_required
    def get(self, batch=None, flag_name=None):
        if batch and flag_name:                # /batch-flags/<location:batch>/<flag_name> or ?location=vijayawada
            location = None
            actual_batch = batch
            
            # Parse location:batch format
            if ":" in batch:
                location, actual_batch = batch.split(":", 1)
            
            # Check query parameter
            if not location:
                location = request.args.get("location")
            
            # Location is required
            if not location:
                return {
                    "success": False,
                    "msg": "Location is required. Use ?location=vijayawada or location:batch format"
                }, 400
            
            return {
                "batch": actual_batch,
                "flag_name": flag_name,
                "location": location,
                "enabled": is_enabled_for_batch(flag_name, actual_batch, location)
            }, 200
        elif batch:                            # /batch-flags/<batch>
            return _load_batch_flags().get(batch, {}), 200
        else:                                     # /batch-flags (all flags by batch)
            return _load_batch_flags(), 200

    @admin_required
    def post(self, batch, flag_name):
        body = request.get_json(force=True)
        if "enabled" not in body or not isinstance(body["enabled"], bool):
            return {
                "success": False,
                "msg": "`enabled` boolean required."
            }, 400

        location = body.get("location")
        set_batch_flag(flag_name, batch, body["enabled"], location)
        return {
            "success": True,
            "batch": batch,
            "flag_name": flag_name,
            "enabled": is_enabled_for_batch(flag_name, batch)
        }, 200


class HierarchicalFeatureView(Resource):
    """API for hierarchical view of feature flags across global, locations, and batches."""
    @Hierarchical_Feature_View
    def get(self, flag_name=None):
        # If no flag name provided, return only flagcodePlayground
        if not flag_name:
            return {"flagcodePlayground": self._build_hierarchy_for_flag("flagcodePlayground")}, 200
        
        # Return hierarchy for specific flag
        return self._build_hierarchy_for_flag(flag_name), 200
    
    def _build_hierarchy_for_flag(self, flag_name):
        # Get global status
        global_status = is_enabled(flag_name)
        
        # Get all locations
        location_flags = _load_location_flags()
        locations = {}
        
        # Add global location
        if "global" in location_flags and flag_name in location_flags["global"]:
            locations["global"] = location_flags["global"][flag_name]
        else:
            locations["global"] = global_status
        
        # Add other locations
        for location, flags in location_flags.items():
            if location != "global" and flag_name in flags:
                locations[location] = flags[flag_name]
        
        # Get all batches
        batch_flags = _load_batch_flags()
        batches = {}
        
        # Add global batch setting
        if "global" in batch_flags and flag_name in batch_flags["global"]:
            batches["global"] = batch_flags["global"][flag_name]
        
        # Add other batches using stored location from batch flag documents
        from web.Exam.exam_central_db import batch_flags_collection
        batch_docs = batch_flags_collection.find({"flag_name": flag_name})
        
        for batch_doc in batch_docs:
            batch = batch_doc.get("batch")
            if batch and batch != "global":
                batch_location = batch_doc.get("location", "unknown")
                
                if batch_location not in batches:
                    batches[batch_location] = {}
                
                batches[batch_location][batch] = {
                    "enabled": batch_doc.get("enabled", False)
                }
        
        # Build final hierarchy
        return {
            "global": global_status,
            "locations": locations,
            "batches": batches,
            "explanation": "Hierarchical check: global -> location -> batch. All applicable flags must be TRUE for the feature to be enabled. If global flag is FALSE, feature is disabled for everyone. If location flag is FALSE, feature is disabled for that location. Batch settings cannot override global or location settings."
        }