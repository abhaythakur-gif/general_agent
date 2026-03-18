"""
app/config/logging.py
----------------------
Logging initialisation for the whole platform.
Provides a factory function `get_logger(name)` that every module imports.
"""

import json
import logging
from datetime import datetime

from app.config.settings import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for extra_key in ("workflow_id", "agent_name", "event", "tool", "duration_ms"):
            if hasattr(record, extra_key):
                log_entry[extra_key] = getattr(record, extra_key)
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger
