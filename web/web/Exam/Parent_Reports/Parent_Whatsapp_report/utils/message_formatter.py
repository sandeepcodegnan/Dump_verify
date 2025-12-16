"""
Centralized message formatting
"""

class MessageFormatter:
    @staticmethod
    def format_completion_message(cumulative_students, total_locations_processed, cumulative_completed_batches, total_time):
        """Format final completion message"""
        message_parts = [
            f"Generated {cumulative_students} PDFs",
            f"across {total_locations_processed} locations", 
            f"and {cumulative_completed_batches} batches",
            f"in this execution ({total_time:.1f}s)"
        ]
        return " ".join(message_parts)
    
    @staticmethod
    def format_batch_message(processed_batches, skipped_batches, total_batches):
        """Format batch processing message"""
        return f"PDF: {processed_batches} completed, {skipped_batches} skipped of {total_batches} total batches"
    
    @staticmethod
    def format_location_message(location_name, student_count):
        """Format location processing message"""
        return f"Processed {student_count} students in {location_name}"