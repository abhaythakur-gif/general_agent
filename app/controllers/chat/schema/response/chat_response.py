"""
app/controllers/chat/schema/response/chat_response.py
======================================================
Pydantic response schemas for the Chat controller.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Building block
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    """A single chat message (user or assistant turn)."""

    id: str
    session_id: str
    user_id: str
    tenant_id: str
    role: str              # "user" | "assistant"
    content: str
    timestamp: str
    metadata: dict = {}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class ChatSessionOut(BaseModel):
    """
    Full chat session document.

    Returned by:
    - ``POST /chat/sessions`` (on creation)
    - ``GET  /chat/sessions/{session_id}``
    """

    id: str
    user_id: str
    tenant_id: str
    title: str
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    llm_model: str
    created_at: str
    last_message_at: str
    message_count: int


class ChatSessionListOut(BaseModel):
    """
    All sessions for a user.

    Returned by ``GET /chat/sessions``.
    """

    sessions: List[ChatSessionOut]
    total: int


# ---------------------------------------------------------------------------
# Message / reply
# ---------------------------------------------------------------------------

class ChatReplyOut(BaseModel):
    """
    The assistant's reply and the full up-to-date message history.

    Returned by ``POST /chat/sessions/{session_id}/message``.
    """

    session_id: str
    tenant_id: str
    reply: str
    history: List[MessageOut]


class ChatHistoryOut(BaseModel):
    """
    Full message history for a session.

    Returned by ``GET /chat/sessions/{session_id}/history``.
    """

    session_id: str
    tenant_id: str
    messages: List[MessageOut]
    total: int


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class ChatSessionDeleteOut(BaseModel):
    """Confirmation that a session was deleted."""

    deleted: bool
    session_id: str
