"""JSON structured logging with correlation ID support."""

import json
import logging
import sys
import time
from typing import Any, Dict

def configure_json_logging():
    """Configure JSON structured logging to stdout."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create new handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))  # Raw JSON lines
    logger.addHandler(handler)

def log_json(event: str, **fields: Any):
    """Log a structured JSON event.
    
    Args:
        event: Event type/name
        **fields: Additional fields to include in log
    """
    log_entry = {
        "event": event,
        "timestamp": time.time(),
        **fields
    }
    logging.getLogger().info(json.dumps(log_entry))

class Timer:
    """Context manager for timing operations."""
    
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self
    
    def __exit__(self, *exc):
        self.dt = time.perf_counter() - self.t0