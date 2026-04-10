"""
app/controllers/agent/schema/response/agent_response.py
========================================================
Pydantic response schemas for the Agent controller.

These models define exactly what every Agent endpoint returns so that
FastAPI can serialise and validate outbound JSON automatically.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared building block
# ---------------------------------------------------------------------------

class FieldSchemaOut(BaseModel):
    """Single input / output field attached to an agent definition."""

    name: str
    type: str = "str"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Single agent
# ---------------------------------------------------------------------------

class AgentOut(BaseModel):
    """
    Full representation of a persisted agent.

    Returned by:
    - ``POST /agents`` (on creation)
    - ``GET  /agents/{agent_id}``
    - ``PUT  /agents/{agent_id}``
    """

    id: str
    name: str
    description: str
    agent_type: str
    behavior: str
    llm_model: Optional[str] = None
    tools: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    input_schema: List[FieldSchemaOut] = []
    output_schema: List[FieldSchemaOut] = []
    run_if: Optional[str] = None
    user_id: str
    created_at: str


# ---------------------------------------------------------------------------
# List of agents
# ---------------------------------------------------------------------------

class AgentListOut(BaseModel):
    """
    Paginated list of agents for a user.

    Returned by ``GET /agents``.
    """

    agents: List[AgentOut]
    total: int


# ---------------------------------------------------------------------------
# Delete confirmation
# ---------------------------------------------------------------------------

class AgentDeleteOut(BaseModel):
    """
    Confirmation that an agent was deleted.

    Returned by ``DELETE /agents/{agent_id}``.
    """

    deleted: bool
    agent_id: str
