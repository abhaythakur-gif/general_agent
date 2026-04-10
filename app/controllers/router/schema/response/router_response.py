"""
app/controllers/router/schema/response/router_response.py
==========================================================
Pydantic response schemas for the Custom Router controller.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Single router
# ---------------------------------------------------------------------------

class RouterOut(BaseModel):
    """
    Full custom router document.

    Returned by:
    - ``POST /routers`` (on creation)
    - ``GET  /routers/{router_id}``
    - ``PUT  /routers/{router_id}``
    """

    id: str
    name: str
    description: str
    user_id: str
    workflow_ids: List[str]
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# List of routers
# ---------------------------------------------------------------------------

class RouterListOut(BaseModel):
    """
    All custom routers for a user.

    Returned by ``GET /routers``.
    """

    routers: List[RouterOut]
    total: int


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class RouterDeleteOut(BaseModel):
    """Confirmation that a router was deleted."""

    deleted: bool
    router_id: str


# ---------------------------------------------------------------------------
# Dispatch result
# ---------------------------------------------------------------------------

class RouterDispatchOut(BaseModel):
    """
    Result of dispatching a natural-language query to a router.

    Returned by ``POST /routers/{router_id}/dispatch``.

    | Field               | Description                                             |
    |---------------------|---------------------------------------------------------|
    | ``selected_workflow_id`` | The workflow the LLM selected                   |
    | ``execution_id``    | ID of the execution that was started                    |
    | ``status``          | ``completed`` | ``paused`` | ``failed``               |
    | ``final_output``    | The workflow's output (when ``status == "completed"``)  |
    | ``follow_up_question`` | Present when ``status == "paused"``                |
    | ``missing_fields``  | Fields the paused agent is waiting for                  |
    """

    selected_workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    status: str
    final_output: Optional[Dict[str, Any]] = None
    follow_up_question: Optional[str] = None
    missing_fields: List[str] = []
    error: Optional[str] = None
