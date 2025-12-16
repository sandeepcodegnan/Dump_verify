"""
Processing coordination to separate concerns
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from web.Exam.Parent_Reports.Parent_Whatsapp_report.utils.tracker_manager import TrackerManager


class ProcessingCoordinator:
    def __init__(self, report_type, force=False, batch_processor=None):
        from web.Exam.Parent_Reports.Parent_Whatsapp_report.orchestration.processing_orchestrator import ProcessingOrchestrator
        self._delegate = ProcessingOrchestrator(report_type, force, batch_processor)

    def process_location_batches(self, batches, period_id, start_date, end_date, tracker):
        return self._delegate.process_location_batches(batches, period_id, start_date, end_date, tracker)
