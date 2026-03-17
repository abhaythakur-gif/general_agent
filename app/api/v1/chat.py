"""
app/api/v1/chat.py
-------------------
FastAPI router for the persistent chat / memory feature.

All routes require the `X-User-ID` header (standard platform auth).

Endpoints:
  POST   /chat/sessions                          → create session
  GET    /chat/sessions                          → list sessions
  GET    /chat/sessions/by-tenant/{tenant_id}    → look up session by tenant label
  GET    /chat/sessions/{session_id}             → get single session
  DELETE /chat/sessions/{session_id}             → delete session + history
  POST   /chat/sessions/{session_id}/messages    → send message, receive reply
  GET    /chat/sessions/{session_id}/messages    → fetch message history
  DELETE /chat/sessions/{session_id}/messages    → clear session history
"""

from fastapi import APIRouter, Depends, Query
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionListResponse,
    ChatResponse,
    ChatHistoryResponse,
)
from app.services.auth_service import get_current_user_id
from app.schemas.chat import ChatMessageCreate
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat Memory"])


# ─── Session endpoints ────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    summary="Create a new chat session",
    response_model=ChatSessionOut,
    status_code=201,
)
def create_session(
    data: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new chat session scoped to the current user.

    **`tenant_id`** is a human-readable label you assign (e.g. `"travel-planner"`).
    Pass it again in a future session to resume the conversation.
    """
    return chat_service.create_session(data, user_id)


@router.get(
    "/sessions",
    summary="List all chat sessions for the current user",
    response_model=ChatSessionListResponse,
)
def list_sessions(user_id: str = Depends(get_current_user_id)):
    return chat_service.list_sessions(user_id)


@router.get(
    "/sessions/by-tenant/{tenant_id}",
    summary="Look up the latest session by tenant_id label",
    response_model=ChatSessionOut,
    responses={404: {"description": "No session found for this tenant_id"}},
)
def get_by_tenant(tenant_id: str, user_id: str = Depends(get_current_user_id)):
    session = chat_service.get_session_by_tenant(user_id, tenant_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No session found for tenant_id '{tenant_id}'")
    return session


@router.get(
    "/sessions/{session_id}",
    summary="Get a single chat session",
    response_model=ChatSessionOut,
    responses={404: {"description": "Session not found"}},
)
def get_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    return chat_service.get_session(session_id, user_id)


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a session and all its messages",
    responses={404: {"description": "Session not found"}},
)
def delete_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    return chat_service.delete_session(session_id, user_id)


# ─── Message endpoints ────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a user message and receive the assistant reply",
    response_model=ChatResponse,
    responses={404: {"description": "Session not found"}, 500: {"description": "LLM error"}},
)
def send_message(
    session_id: str,
    data: ChatMessageCreate,
    user_id: str = Depends(get_current_user_id),
):
    """
    Send a message to the LLM in the context of this session.
    The last 20 turns of history are automatically included in the prompt.
    Both the user message and the assistant reply are stored in MongoDB.
    """
    return chat_service.send_message(session_id, user_id, data.content)


@router.get(
    "/sessions/{session_id}/messages",
    summary="Fetch message history for a session",
    response_model=ChatHistoryResponse,
    responses={404: {"description": "Session not found"}},
)
def get_history(
    session_id: str,
    limit: int = Query(default=30, ge=1, le=200, description="Max number of messages to return"),
    user_id: str = Depends(get_current_user_id),
):
    return chat_service.get_history(session_id, user_id, limit=limit)


@router.delete(
    "/sessions/{session_id}/messages",
    summary="Clear all messages in a session (keep the session itself)",
    responses={404: {"description": "Session not found"}},
)
def clear_history(session_id: str, user_id: str = Depends(get_current_user_id)):
    return chat_service.clear_session_history(session_id, user_id)
