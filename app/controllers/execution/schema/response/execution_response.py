"""
app/controllers/execution/schema/response/execution_response.py
================================================================
Pydantic response schemas for the Execution controller.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Trigger / resume response
# ---------------------------------------------------------------------------

class ExecutionOut(BaseModel):
    """
    Lightweight execution result returned immediately after triggering or
    resuming a run.

    ### Status values
    | Value       | Meaning                                                  |
    |-------------|----------------------------------------------------------|
    | ``completed`` | The workflow finished; ``final_output`` is populated   |
    | ``paused``    | An agent needs more information; ``follow_up_question`` and ``missing_fields`` are populated |
    | ``failed``    | An unrecoverable error occurred                        |

    Returned by:
    - ``POST /workflows/{workflow_id}/execute``
    - ``POST /executions/{execution_id}/resume``
    """

    execution_id: str
    status: str
    final_output: Optional[Dict[str, Any]] = None
    follow_up_question: Optional[str] = None
    paused_at_agent: Optional[str] = None
    missing_fields: List[str] = []


# ---------------------------------------------------------------------------
# Detailed execution (includes logs)
# ---------------------------------------------------------------------------

class ExecutionDetailOut(BaseModel):
    """
    Full execution document with status, result, and per-step log entries.

    Returned by ``GET /executions/{execution_id}``.
    """

    id: str
    workflow_id: str
    user_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    log_entries: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Logs-only view
# ---------------------------------------------------------------------------

class ExecutionLogsOut(BaseModel):
    """
    Step-by-step agent log entries for debugging a specific execution.

    Returned by ``GET /executions/{execution_id}/logs``.
    """

    execution_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    log_entries: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# List of executions
# ---------------------------------------------------------------------------

class ExecutionListOut(BaseModel):
    """
    All past executions for a user.

    Returned by ``GET /executions``.
    """

    executions: List[ExecutionDetailOut]
    total: int
