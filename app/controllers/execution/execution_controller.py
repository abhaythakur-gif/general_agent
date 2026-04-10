"""
app/controllers/execution/execution_controller.py
==================================================
FastAPI router that handles all **Execution** HTTP endpoints.

Design principles
-----------------
* **Controller** — receives HTTP requests, validates them, delegates to
  ``app.services.execution_service``, and returns serialised responses.
* Execution is *stateful*: a run can be completed, paused (mid-flight
  waiting for user input), or failed.
* Log entries are stored in MongoDB for debugging and audit.

Execution lifecycle
-------------------
```
[POST /workflows/{id}/execute]
        │
        ▼
   status=running
        │
   ┌────┴─────────┐
   │              │
completed      paused
   │              │
   ▼         [POST /executions/{id}/resume]
 done              │
              status=running
                   │
              (may pause again or complete)
```

Authentication
--------------
- ``POST  /workflows/{id}/execute`` — requires ``X-User-ID`` header.
- ``GET   /executions``             — requires ``X-User-ID`` header.
- ``POST  /executions/{id}/resume`` — *no auth required* (resume token serves as auth).
- ``GET   /executions/{id}``        — *no auth required* (execution_id is the token).
- ``GET   /executions/{id}/logs``   — *no auth required*.

Prefix
------
Execution routes do *not* share a common prefix because they span two
resource paths: ``/workflows`` and ``/executions``.  Both groups are
registered on this single router and mounted in ``main.py``.
"""

from fastapi import APIRouter, Depends, Path, status

from app.controllers.execution.schema.request.execution_request import (
    ExecuteWorkflowRequest,
    ResumeExecutionRequest,
)
from app.controllers.execution.schema.response.execution_response import (
    ExecutionDetailOut,
    ExecutionListOut,
    ExecutionLogsOut,
    ExecutionOut,
)
from app.services.auth.service import get_current_user_id
from app.services.execution import service as execution_service

# ---------------------------------------------------------------------------
# Router — no shared prefix (spans /workflows and /executions)
# ---------------------------------------------------------------------------

router = APIRouter(
    tags=["Execution"],
    responses={
        422: {"description": "Request body failed Pydantic validation"},
    },
)


# ---------------------------------------------------------------------------
# POST /workflows/{workflow_id}/execute  — trigger a run
# ---------------------------------------------------------------------------

@router.post(
    "/workflows/{workflow_id}/execute",
    summary="Trigger a workflow execution",
    description="""
## Execute a workflow

Starts a synchronous workflow run for the given workflow ID.

The run blocks until the workflow either **completes** or **pauses**
waiting for additional user input.

### Authentication
Requires the ``X-User-ID`` header.

### Status values
| ``status``    | Meaning                                                    |
|---------------|------------------------------------------------------------|
| ``completed`` | All agents ran successfully; ``final_output`` is populated |
| ``paused``    | An agent needs more info; ``follow_up_question`` explains what is needed |
| ``failed``    | An unrecoverable error occurred                            |

### Example request
```json
{
  "initial_inputs": {
    "text": "I love this product, it exceeded all my expectations!"
  }
}
```

### Example response — completed
```json
{
  "execution_id": "<uuid>",
  "status": "completed",
  "final_output": { "sentiment": "positive", "confidence": 0.97 }
}
```

### Example response — paused
```json
{
  "execution_id": "<uuid>",
  "status": "paused",
  "follow_up_question": "What is your departure date?",
  "paused_at_agent": "Travel Planner",
  "missing_fields": ["departure_date"]
}
```
""",
    response_model=ExecutionOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Execution completed or paused"},
        404: {"description": "Workflow or a referenced agent not found"},
        500: {"description": "Unhandled runner error"},
    },
)
def execute_workflow(
    data: ExecuteWorkflowRequest,
    workflow_id: str = Path(..., description="UUID of the workflow to execute"),
    user_id: str = Depends(get_current_user_id),
) -> ExecutionOut:
    """Trigger a workflow execution and return the result or pause state."""
    return execution_service.execute_workflow(
        workflow_id=workflow_id,
        initial_inputs=data.initial_inputs,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# POST /executions/{execution_id}/resume  — resume a paused run
# ---------------------------------------------------------------------------

@router.post(
    "/executions/{execution_id}/resume",
    summary="Resume a paused execution",
    description="""
## Resume a paused execution

When a workflow pauses and returns a ``follow_up_question``, call this
endpoint to supply the user's answer and continue the run from where it
stopped.

### No auth required
The ``execution_id`` itself acts as a resumption token.

### Example request
```json
{ "user_input": "My departure date is June 1st 2026" }
```

### Example response — now completed after resume
```json
{
  "execution_id": "<uuid>",
  "status": "completed",
  "final_output": {
    "flights": [
      { "airline": "Air France", "price": 450, "departure": "2026-06-01T08:00Z" }
    ]
  }
}
```
""",
    response_model=ExecutionOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Execution continued (completed or paused again)"},
        404: {"description": "Execution not found or not currently paused"},
    },
)
def resume_execution(
    data: ResumeExecutionRequest,
    execution_id: str = Path(..., description="UUID of the paused execution to resume"),
) -> ExecutionOut:
    """Resume a paused execution with the user's answer."""
    return execution_service.resume_execution(
        execution_id=execution_id,
        user_input=data.user_input,
    )


# ---------------------------------------------------------------------------
# GET /executions/{execution_id}  — fetch execution detail
# ---------------------------------------------------------------------------

@router.get(
    "/executions/{execution_id}",
    summary="Get execution status and result",
    description="""
## Get execution

Returns the full execution document including status, timestamps, final
output, and per-step log entries.

### No auth required
The ``execution_id`` is the access token.

### Response shape
```json
{
  "id": "<uuid>",
  "workflow_id": "<workflow-uuid>",
  "user_id": "abhay-123",
  "status": "completed",
  "started_at": "2026-03-19T10:00:00Z",
  "completed_at": "2026-03-19T10:00:04Z",
  "final_output": { "sentiment": "positive" },
  "log_entries": [
    { "agent": "Sentiment Analyser", "status": "success", "output": { "sentiment": "positive" } }
  ]
}
```
""",
    response_model=ExecutionDetailOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Execution document"},
        404: {"description": "Execution not found"},
    },
)
def get_execution(
    execution_id: str = Path(..., description="UUID of the execution to retrieve"),
) -> ExecutionDetailOut:
    """Fetch full execution detail by ID."""
    return execution_service.get_execution(execution_id)


# ---------------------------------------------------------------------------
# GET /executions/{execution_id}/logs  — fetch step logs
# ---------------------------------------------------------------------------

@router.get(
    "/executions/{execution_id}/logs",
    summary="Get step-by-step agent logs for an execution",
    description="""
## Get execution logs

Returns only the ``log_entries`` array for a given execution — useful for
streaming a debug view in the UI without loading the full output.

### No auth required

### Log entry shape
```json
{
  "step": 1,
  "agent": "Search Agent",
  "status": "success",
  "input": { "query": "best hotels in Paris" },
  "output": { "results": ["..."] },
  "duration_ms": 1234
}
```
""",
    response_model=ExecutionLogsOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Log entries for the execution"},
        404: {"description": "Execution not found"},
    },
)
def get_execution_logs(
    execution_id: str = Path(..., description="UUID of the execution whose logs to retrieve"),
) -> ExecutionLogsOut:
    """Fetch per-step agent logs for a specific execution."""
    return execution_service.get_execution_logs(execution_id)


# ---------------------------------------------------------------------------
# GET /executions  — list all executions for user
# ---------------------------------------------------------------------------

@router.get(
    "/executions",
    summary="List all past executions for the current user",
    description="""
## List executions

Returns every execution triggered by the authenticated user, ordered by
most recent first.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{
  "executions": [ { ...ExecutionDetailOut... } ],
  "total": 12
}
```
""",
    response_model=ExecutionListOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of executions (may be empty)"},
        401: {"description": "X-User-ID header is missing"},
    },
)
def list_executions(
    user_id: str = Depends(get_current_user_id),
) -> ExecutionListOut:
    """Return all past executions for the authenticated user."""
    executions = execution_service.list_executions(user_id)
    return ExecutionListOut(executions=executions, total=len(executions))
