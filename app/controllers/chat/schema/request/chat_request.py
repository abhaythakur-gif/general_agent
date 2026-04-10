"""
app/controllers/chat/schema/request/chat_request.py
====================================================
Pydantic request schemas for the Chat controller.

The Chat module provides conversational interfaces over agents and
workflows.  A *session* holds multi-turn message history; each call to
``POST /chat/sessions/{session_id}/message`` adds a user turn and
returns the assistant reply.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# SESSION
# ---------------------------------------------------------------------------

class CreateChatSessionRequest(BaseModel):
    """
    Request body for **POST /chat/sessions**.

    ### Required fields
    | Field        | Description                                              |
    |--------------|----------------------------------------------------------|
    | ``tenant_id``| Human-readable session label used as a namespace key    |

    ### Optional fields
    | Field          | Default     | Description                                             |
    |----------------|-------------|-------------------------------------------------------- |
    | ``title``      | ``""``      | Display title shown in the UI sidebar                  |
    | ``workflow_id``| ``null``    | Attach a workflow — messages will trigger workflow runs |
    | ``agent_id``   | ``null``    | Attach a single agent — messages go directly to it     |
    | ``llm_model``  | ``"gpt-4"`` | Override the default LLM for this session              |

    > Exactly one of ``workflow_id`` or ``agent_id`` should be set, or
    > neither (plain LLM chat).

    ### Example — workflow-backed session
    ```json
    {
      "tenant_id": "travel-planner",
      "title": "Paris Trip Planning",
      "workflow_id": "<workflow-uuid>",
      "llm_model": "gpt-4o"
    }
    ```

    ### Example — agent-backed session
    ```json
    {
      "tenant_id": "support-bot",
      "title": "Customer Support",
      "agent_id": "<agent-uuid>"
    }
    ```
    """

    tenant_id: str = Field(..., min_length=1, description="Human-readable session namespace key")
    title: str = Field("", description="Optional display title shown in the UI")
    workflow_id: Optional[str] = Field(None, description="Attach an existing workflow to this session")
    agent_id: Optional[str] = Field(None, description="Attach a single agent to this session")
    llm_model: str = Field("gpt-4", description="LLM model to use in this session (see GET /models)")


# ---------------------------------------------------------------------------
# MESSAGE
# ---------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    """
    Request body for **POST /chat/sessions/{session_id}/message**.

    ### Example
    ```json
    { "content": "What flights are available from New York to Paris in June?" }
    ```
    """

    content: str = Field(..., min_length=1, description="The user's message text")
