import logging
import json
from datetime import datetime
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "workflow_id"):
            log_entry["workflow_id"] = record.workflow_id
        if hasattr(record, "agent_name"):
            log_entry["agent_name"] = record.agent_name
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "tool"):
            log_entry["tool"] = record.tool
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    return logger
