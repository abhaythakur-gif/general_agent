"""
app/controllers/chat/chat_controller.py
=========================================
FastAPI router that handles all **Chat** HTTP endpoints.

Design principles
-----------------
* **Controller** — thin HTTP layer; delegates to ``app.services.chat_service``.
* Chat is *session-based*: a session persists multi-turn conversation
  history in MongoDB and optionally ties every message exchange to an
  existing workflow or agent.
* The service layer manages the LLM invocation and message persistence.

Session model
-------------
```
POST /chat/sessions                 → create a session
POST /chat/sessions/{id}/message    → send a message; get LLM reply + history
GET  /chat/sessions/{id}/history    → read full message history
DELETE /chat/sessions/{id}/history  → clear messages (keep session)
GET  /chat/sessions/{id}            → inspect session metadata
GET  /chat/sessions                 → list all sessions
DELETE /chat/sessions/{id}          → delete a session
```

Authentication
--------------
All routes require the ``X-User-ID`` header.

Prefix
------
Mounted at ``/api/v1/chat`` in ``main.py``.
"""

from fastapi import APIRouter, Depends, Path, Query, status

from app.controllers.chat.schema.request.chat_request import (
    CreateChatSessionRequest,
    SendMessageRequest,
)
from app.controllers.chat.schema.response.chat_response import (
    ChatHistoryOut,
    ChatReplyOut,
    ChatSessionDeleteOut,
    ChatSessionListOut,
    ChatSessionOut,
)
from app.services.auth.service import get_current_user_id
from app.services.session.core import session_manager as chat_service

# We re-use the existing ChatSessionCreate schema that the service expects
from app.controllers.schema.request_schema.chat import (
    ChatSessionCreate as _ServiceSessionCreate,
)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    responses={
        401: {"description": "X-User-ID header is missing"},
        422: {"description": "Request body failed Pydantic validation"},
    },
)


# ---------------------------------------------------------------------------
# POST /chat/sessions  — create a session
# ---------------------------------------------------------------------------

@router.post(
    "/sessions",
    summary="Create a new chat session",
    description="""
## Create chat session

Creates a named, persistent chat session in MongoDB.  Each session
stores the full multi-turn message history.

### Session modes

| Mode       | How to set it                            | Behaviour                                  |
|------------|------------------------------------------|--------------------------------------------|
| Plain LLM  | Neither ``workflow_id`` nor ``agent_id`` | Direct multi-turn LLM conversation          |
| Workflow   | Set ``workflow_id``                      | Each message triggers a full workflow run  |
| Agent      | Set ``agent_id``                         | Each message is sent directly to one agent |

### Authentication
Requires the ``X-User-ID`` header.

### Example — plain LLM session
```json
{
  "tenant_id": "general-chat",
  "title": "General Assistant",
  "llm_model": "gpt-4o"
}
```

### Example — workflow-backed session
```json
{
  "tenant_id": "travel-planner",
  "title": "Paris Trip 2026",
  "workflow_id": "<workflow-uuid>",
  "llm_model": "gpt-4"
}
```
""",
    response_model=ChatSessionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Session created"},
    },
)
def create_session(
    data: CreateChatSessionRequest,
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionOut:
    """Create and persist a new chat session."""
    svc_data = _ServiceSessionCreate(
        tenant_id=data.tenant_id,
        title=data.title,
        workflow_id=data.workflow_id,
        agent_id=data.agent_id,
        llm_model=data.llm_model,
    )
    return chat_service.create_session(svc_data, user_id)


# ---------------------------------------------------------------------------
# GET /chat/sessions  — list all sessions
# ---------------------------------------------------------------------------

@router.get(
    "/sessions",
    summary="List all chat sessions for the current user",
    description="""
## List sessions

Returns every chat session owned by the authenticated user, sorted by
most recent message first.

### Authentication
Requires the ``X-User-ID`` header.
""",
    response_model=ChatSessionListOut,
    status_code=status.HTTP_200_OK,
)
def list_sessions(
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionListOut:
    """List all chat sessions for the authenticated user."""
    result = chat_service.list_sessions(user_id)
    # result is a ChatSessionListResponse (sessions, total)
    return ChatSessionListOut(sessions=result.sessions, total=result.total)


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}  — get one session
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{session_id}",
    summary="Get a chat session by ID",
    description="""
## Get session

Fetches a single chat session by its UUID.

### Authentication
Requires the ``X-User-ID`` header.
""",
    response_model=ChatSessionOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Session found"},
        404: {"description": "Session not found"},
    },
)
def get_session(
    session_id: str = Path(..., description="UUID of the session to retrieve"),
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionOut:
    """Fetch a chat session by ID."""
    return chat_service.get_session(session_id, user_id)


# ---------------------------------------------------------------------------
# POST /chat/sessions/{session_id}/message  — send a message
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a message and receive an LLM reply",
    description="""
## Send message

Appends a user turn to the session's message history, invokes the
configured LLM (or workflow), persists the assistant reply, and returns
the updated history.

### Authentication
Requires the ``X-User-ID`` header.

### How history is managed
- The last **20 messages** are included in every LLM call to maintain context.
- All messages (user + assistant) are stored permanently in MongoDB.

### Example request
```json
{ "content": "What flights are available from New York to Paris in June?" }
```

### Example response
```json
{
  "session_id": "<uuid>",
  "tenant_id": "travel-planner",
  "reply": "I found several options.  The cheapest is Air France for $450 …",
  "history": [
    { "role": "user",      "content": "What flights …", "timestamp": "…" },
    { "role": "assistant", "content": "I found …",       "timestamp": "…" }
  ]
}
```
""",
    response_model=ChatReplyOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "LLM reply and updated history"},
        404: {"description": "Session not found"},
        500: {"description": "LLM invocation error"},
    },
)
def send_message(
    data: SendMessageRequest,
    session_id: str = Path(..., description="UUID of the session to send the message to"),
    user_id: str = Depends(get_current_user_id),
) -> ChatReplyOut:
    """Send a user message and return the assistant reply with history."""
    result = chat_service.send_message(session_id, user_id, data.content)
    return ChatReplyOut(
        session_id=result.session_id,
        tenant_id=result.tenant_id,
        reply=result.reply,
        history=result.history,
    )


# ---------------------------------------------------------------------------
# GET /chat/sessions/by-tenant/{tenant_id}  — get session by tenant label
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/by-tenant/{tenant_id}",
    summary="Look up the latest session by tenant_id label",
    description="""
## Get session by tenant

Looks up the most recent session with the given ``tenant_id`` for the
authenticated user.  Useful when you store a human-readable label and
need to resume the associated session.

### Authentication
Requires the ``X-User-ID`` header.

### Example
```
GET /api/v1/chat/sessions/by-tenant/travel-planner
X-User-ID: abhay-123
```
""",
    response_model=ChatSessionOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Session found"},
        404: {"description": "No session found for this tenant_id"},
    },
)
def get_session_by_tenant(
    tenant_id: str = Path(..., description="Human-readable tenant label to look up"),
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionOut:
    """Fetch the most recent session matching *tenant_id* for the authenticated user."""
    session = chat_service.get_session_by_tenant(user_id, tenant_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No session found for tenant_id '{tenant_id}'")
    return session


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}/messages  — get message history
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{session_id}/messages",
    summary="Get the full message history of a session",
    description="""
## Get history

Returns the full message history for a session (up to the requested
``limit``).

### Authentication
Requires the ``X-User-ID`` header.

### Query parameters
| Parameter | Default | Description                              |
|-----------|---------|------------------------------------------|
| ``limit`` | 30      | Maximum number of messages to return     |
""",
    response_model=ChatHistoryOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Message history"},
        404: {"description": "Session not found"},
    },
)
def get_history(
    session_id: str = Path(..., description="UUID of the session"),
    limit: int = Query(30, ge=1, le=200, description="Maximum messages to return"),
    user_id: str = Depends(get_current_user_id),
) -> ChatHistoryOut:
    """Return the message history for a session."""
    result = chat_service.get_history(session_id, user_id, limit=limit)
    return ChatHistoryOut(
        session_id=result.session_id,
        tenant_id=result.tenant_id,
        messages=result.messages,
        total=result.total,
    )


# ---------------------------------------------------------------------------
# DELETE /chat/sessions/{session_id}/history  — clear messages
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}/messages",
    summary="Clear all messages in a session (keep session)",
    description="""
## Clear history

Deletes all messages in the session without removing the session itself.
Useful for starting a fresh conversation within the same session.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{ "cleared": true, "session_id": "<uuid>", "messages_deleted": 14 }
```
""",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "History cleared"},
        404: {"description": "Session not found"},
    },
)
def clear_history(
    session_id: str = Path(..., description="UUID of the session whose history to clear"),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Clear all messages in a session."""
    return chat_service.clear_session_history(session_id, user_id)


# ---------------------------------------------------------------------------
# DELETE /chat/sessions/{session_id}  — delete a session
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session",
    description="""
## Delete session

Permanently removes the session and all its messages from MongoDB.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{ "deleted": true, "session_id": "<uuid>" }
```
""",
    response_model=ChatSessionDeleteOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Session deleted"},
        404: {"description": "Session not found"},
    },
)
def delete_session(
    session_id: str = Path(..., description="UUID of the session to delete"),
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionDeleteOut:
    """Delete a chat session and all its messages."""
    result = chat_service.delete_session(session_id, user_id)
    return ChatSessionDeleteOut(deleted=result["deleted"], session_id=result["session_id"])
