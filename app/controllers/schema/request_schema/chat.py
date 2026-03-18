"""
app/controllers/schema/request_schema/chat.py
-----------------------------------------------
Request + response schemas for chat endpoints.
(Response types that are tightly coupled to request flow live here too.)
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Request schemas ──────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1, description="Human-readable session label")
    title: str = Field("", description="Optional display title for the session")
    workflow_id: Optional[str] = Field(None, description="Attach an existing workflow to this session")
    agent_id: Optional[str] = Field(None, description="Attach a single agent to this session")
    llm_model: str = Field("gpt-4", description="LLM model to use in this session")


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="The user's message text")


# ─── Shared data shapes ───────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    user_id: str
    tenant_id: str
    role: str
    content: str
    timestamp: str
    metadata: dict


class ChatSessionOut(BaseModel):
    id: str
    user_id: str
    tenant_id: str
    title: str
    workflow_id: Optional[str]
    agent_id: Optional[str]
    llm_model: str
    created_at: str
    last_message_at: str
    message_count: int


# ─── Response schemas ─────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    session_id: str
    tenant_id: str
    reply: str
    history: List[ChatMessageOut]


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionOut]
    total: int


class ChatHistoryResponse(BaseModel):
    session_id: str
    tenant_id: str
    messages: List[ChatMessageOut]
    total: int
