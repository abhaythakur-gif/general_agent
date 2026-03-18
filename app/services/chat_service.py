"""app/services/chat_service.py — SHIM"""
from app.services.session.core.session_manager import (  # noqa: F401
    create_session, list_sessions, get_session, get_session_by_tenant,
    delete_session, send_message, get_history, clear_session_history,
)
