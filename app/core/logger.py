# app/core/logger.py — SHIM
# Backward-compatibility shim. All logging logic now lives in app/config/logging.py.
from app.config.logging import get_logger, JSONFormatter  # noqa: F401
