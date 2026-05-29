"""Structured logging utility."""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context if available
        if hasattr(record, "context"):
            log_obj["context"] = record.context
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logger(name: str = "ipl_live_score") -> logging.Logger:
    """Setup and return a configured logger."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    return logger

# Global logger instance
logger = setup_logger()

def log_event(action: str, user: Optional[str] = None, result: str = "success", **kwargs):
    """Log an event with standard context fields."""
    context: Dict[str, Any] = {
        "action": action,
        "result": result
    }
    if user:
        context["user"] = user
        
    context.update(kwargs)
    
    extra = {"context": context}
    
    if result == "error":
        logger.error(f"Event: {action} failed", extra=extra)
    else:
        logger.info(f"Event: {action}", extra=extra)
