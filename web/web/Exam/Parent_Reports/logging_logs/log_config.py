"""
Logging configuration for Parent Reports module.
Centralizes all logging setup to follow DRY and SoC principles.
"""
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Constants
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "parent_reports.log")
MAX_LOG_SIZE = 30 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Filter to prevent duplicate log messages
class DuplicateFilter(logging.Filter):
    def __init__(self, name=''):
        super().__init__(name)
        self.last_log = None
        self.last_time = 0
        
    def filter(self, record):
        # Create a key from the message and arguments
        current_log = (record.msg, record.args)
        current_time = time.time()
        
        # If this is the same as the last log and within 0.1 seconds, filter it out
        if current_log == self.last_log and current_time - self.last_time < 0.1:
            return False
            
        self.last_log = current_log
        self.last_time = current_time
        return True

def setup_logging(module_name=None):
    """
    Set up logging for the parent reports module.
    
    Args:
        module_name: Optional name of the module for more specific logging
        
    Returns:
        Logger instance configured with file and console handlers
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Suppress MongoDB connection messages
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    
    # Get logger
    logger_name = f"parent_reports.{module_name}" if module_name else "parent_reports"
    logger = logging.getLogger(logger_name)
    
    # Add duplicate filter
    logger.addFilter(DuplicateFilter())
    
    # Only configure if handlers haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        try:
            # File handler - debug and above
            # Use delay=True to avoid opening the file until first log message
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=MAX_LOG_SIZE,
                backupCount=BACKUP_COUNT,
                delay=True
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # If file handler fails, log to console only
            print(f"Warning: Could not set up file logging: {str(e)}")
        
           
    return logger

def get_logger(module_name=None):
    """
    Get a configured logger instance.
    
    Args:
        module_name: Optional name of the module for more specific logging
        
    Returns:
        Logger instance
    """
    return setup_logging(module_name)