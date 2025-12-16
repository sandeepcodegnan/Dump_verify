"""
Centralized stats creation to eliminate remaining DRY violations
"""

class StatsFactory:
    @staticmethod
    def create_location_processing_stats(locations_count):
        """Create location stats for processing start"""
        return {
            "status": "PROCESSING",
            "total": locations_count,
            "pdf_completed": 0,
            "whatsapp_completed": 0,
            "processing": 0,
            "time_s": 0.0,
            "message": f"Processing {locations_count} locations"
        }
    
    @staticmethod
    def create_location_completion_stats():
        """Create location stats for completion"""
        return {
            "status": "PROCESSING",
            "total": 0,
            "pdf_completed": 1,
            "whatsapp_completed": 0,
            "processing": 0,
            "time_s": 0.0,
            "message": "Location completed"
        }
    
    @staticmethod
    def create_single_location_stats(location, is_new_location):
        """Create stats for single location processing"""
        return {
            "status": "PROCESSING",
            "total": 1 if is_new_location else 0,
            "pdf_completed": -1 if not is_new_location else 0,
            "whatsapp_completed": 0,
            "processing": 1,
            "time_s": 0.0,
            "message": f"Processing {location}"
        }
    
    @staticmethod
    def create_final_location_stats(location, total_time):
        """Create final location stats"""
        return {
            "status": "COMPLETED",
            "total": 0,
            "pdf_completed": 1 if location else 0,
            "whatsapp_completed": 0,
            "processing": -1 if location else 0,
            "time_s": total_time,
            "message": "All locations completed"
        }