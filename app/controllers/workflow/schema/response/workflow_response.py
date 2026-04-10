"""
app/controllers/workflow/schema/response/workflow_response.py
=============================================================
Pydantic response schemas for the Workflow controller.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Single workflow
# ---------------------------------------------------------------------------

class WorkflowOut(BaseModel):
    """
    Full representation of a persisted workflow.

    Returned by:
    - ``POST /workflows`` (on creation)
    - ``GET  /workflows/{workflow_id}``
    - ``PUT  /workflows/{workflow_id}``
    """

    id: str
    name: str
    description: str
    agent_ids: List[str] = []
    workflow_type: str = "sequential"
    conditions: Dict[str, str] = {}
    parallel_groups: List[List[str]] = []
    user_id: str
    created_at: str


# ---------------------------------------------------------------------------
# List of workflows
# ---------------------------------------------------------------------------

class WorkflowListOut(BaseModel):
    """
    All workflows for a user.

    Returned by ``GET /workflows``.
    """

    workflows: List[WorkflowOut]
    total: int


# ---------------------------------------------------------------------------
# Delete confirmation
# ---------------------------------------------------------------------------

class WorkflowDeleteOut(BaseModel):
    """
    Confirmation that a workflow was deleted.

    Returned by ``DELETE /workflows/{workflow_id}``.
    """

    deleted: bool
    workflow_id: str
