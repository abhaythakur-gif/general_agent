"""
app/services/chat_service.py
-----------------------------
Business logic for the persistent chat / memory feature.

Each conversation is identified by:
  • user_id   — who the user is (existing auth layer)
  • tenant_id — a human label the user assigns to a session (e.g. "travel-planner")
  • session_id — auto-generated UUID stored in MongoDB

Flow for every message:
  1. Load the session (or raise 404).
  2. Fetch the last N messages from chat_messages → build LangChain history.
  3. Prepend a system prompt.
  4. Invoke the LLM (or a workflow if `workflow_id` is set on the session).
  5. Persist the user turn and the assistant reply.
  6. Return the assistant reply + updated history.
"""

from __future__ import annotations

from typing import Optional
from fastapi import HTTPException

from app.repositories.repositories import ChatRepository
from app.llm.provider import get_llm
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionOut,
    ChatSessionListResponse,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageOut,
)

_chat_repo = ChatRepository()

# How many previous messages to include in every LLM call
_HISTORY_WINDOW = 20

_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant. "
    "You have access to the conversation history shown below. "
    "Use it to maintain context and give coherent, consistent answers."
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_message_out(doc: dict) -> ChatMessageOut:
    return ChatMessageOut(
        id=doc["id"],
        session_id=doc["session_id"],
        user_id=doc["user_id"],
        tenant_id=doc["tenant_id"],
        role=doc["role"],
        content=doc["content"],
        timestamp=doc["timestamp"],
        metadata=doc.get("metadata", {}),
    )


def _to_session_out(doc: dict) -> ChatSessionOut:
    return ChatSessionOut(
        id=doc["id"],
        user_id=doc["user_id"],
        tenant_id=doc["tenant_id"],
        title=doc.get("title", doc["tenant_id"]),
        workflow_id=doc.get("workflow_id"),
        agent_id=doc.get("agent_id"),
        llm_model=doc.get("llm_model", "gpt-4"),
        created_at=doc["created_at"],
        last_message_at=doc["last_message_at"],
        message_count=doc.get("message_count", 0),
    )


# ─── Session management ───────────────────────────────────────────────────────

def create_session(data: ChatSessionCreate, user_id: str) -> ChatSessionOut:
    doc = _chat_repo.create_session(
        user_id=user_id,
        tenant_id=data.tenant_id,
        title=data.title,
        workflow_id=data.workflow_id,
        agent_id=data.agent_id,
        llm_model=data.llm_model,
    )
    return _to_session_out(doc)


def list_sessions(user_id: str) -> ChatSessionListResponse:
    docs = _chat_repo.list_sessions(user_id)
    sessions = [_to_session_out(d) for d in docs]
    return ChatSessionListResponse(sessions=sessions, total=len(sessions))


def get_session(session_id: str, user_id: str) -> ChatSessionOut:
    doc = _chat_repo.get_session(session_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _to_session_out(doc)


def get_session_by_tenant(user_id: str, tenant_id: str) -> Optional[ChatSessionOut]:
    doc = _chat_repo.get_session_by_tenant(user_id, tenant_id)
    return _to_session_out(doc) if doc else None


def delete_session(session_id: str, user_id: str) -> dict:
    ok = _chat_repo.delete_session(session_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"deleted": True, "session_id": session_id}


# ─── Chat ─────────────────────────────────────────────────────────────────────

def send_message(session_id: str, user_id: str, user_content: str) -> ChatResponse:
    """
    Core chat turn:
      • persist user message
      • build LangChain message list with history
      • call LLM
      • persist assistant reply
      • return reply + updated history
    """
    # 1. Validate session
    session_doc = _chat_repo.get_session(session_id, user_id)
    if not session_doc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    tenant_id = session_doc["tenant_id"]
    llm_model = session_doc.get("llm_model", "gpt-4")

    # 2. Fetch history BEFORE saving the new user message
    history_docs = _chat_repo.get_messages(session_id, user_id, limit=_HISTORY_WINDOW)

    # 3. Build LangChain messages
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    lc_messages = [SystemMessage(content=_SYSTEM_PROMPT)]
    for msg in history_docs:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=user_content))

    # 4. Invoke LLM
    try:
        llm = get_llm(llm_model)
        ai_response = llm.invoke(lc_messages)
        reply_text: str = ai_response.content
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")

    # 5. Persist both turns
    _chat_repo.save_message(
        session_id=session_id,
        user_id=user_id,
        tenant_id=tenant_id,
        role="user",
        content=user_content,
    )
    _chat_repo.save_message(
        session_id=session_id,
        user_id=user_id,
        tenant_id=tenant_id,
        role="assistant",
        content=reply_text,
    )

    # 6. Return updated history (includes the two new turns)
    updated_history = _chat_repo.get_messages(session_id, user_id, limit=_HISTORY_WINDOW)

    return ChatResponse(
        session_id=session_id,
        tenant_id=tenant_id,
        reply=reply_text,
        history=[_to_message_out(m) for m in updated_history],
    )


def get_history(session_id: str, user_id: str, limit: int = 30) -> ChatHistoryResponse:
    doc = _chat_repo.get_session(session_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    msgs = _chat_repo.get_messages(session_id, user_id, limit=limit)
    return ChatHistoryResponse(
        session_id=session_id,
        tenant_id=doc["tenant_id"],
        messages=[_to_message_out(m) for m in msgs],
        total=len(msgs),
    )


def clear_session_history(session_id: str, user_id: str) -> dict:
    doc = _chat_repo.get_session(session_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    deleted = _chat_repo.clear_messages(session_id, user_id)
    return {"cleared": True, "session_id": session_id, "messages_deleted": deleted}
