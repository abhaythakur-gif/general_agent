"""
app/controllers/workflow/workflow_controller.py
===============================================
FastAPI router that handles all **Workflow** HTTP endpoints.

Design principles
-----------------
* **Controller** — thin layer that validates HTTP requests, delegates to
  ``app.services.workflow_service``, and serialises responses.
* All business logic (agent validation, graph construction, persistence)
  lives in the service layer.
* Every route documents its request/response contract inline so the
  Swagger UI at ``/docs`` is self-contained.

Authentication
--------------
All routes require the ``X-User-ID`` header.

Prefix
------
Mounted at ``/api/v1/workflows`` in ``main.py``.
"""

from fastapi import APIRouter, Depends, Path, status

from app.controllers.workflow.schema.request.workflow_request import (
    CreateWorkflowRequest,
    UpdateWorkflowRequest,
)
from app.controllers.workflow.schema.response.workflow_response import (
    WorkflowDeleteOut,
    WorkflowListOut,
    WorkflowOut,
)
from app.services.auth.service import get_current_user_id
from app.services.workflows import service as workflow_service

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
    responses={
        401: {"description": "X-User-ID header is missing"},
        422: {"description": "Request body failed Pydantic validation"},
    },
)


# ---------------------------------------------------------------------------
# POST /workflows  — create a new workflow
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="Create a new workflow",
    description="""
## Create a workflow

Links one or more existing agents into a named workflow and persists the
definition to MongoDB.

### Authentication
Requires the ``X-User-ID`` header.

### Execution strategies
| ``workflow_type`` | Behaviour |
|-------------------|-----------|
| ``sequential`` | Agents run one after the other; output of step N is the input of step N+1 |
| ``conditional`` | Each agent has an optional guard expression; the agent is skipped when the expression is ``False`` |
| ``parallel`` | Groups of agents run concurrently; their outputs are merged before the next step |

### Sequential example
```json
{
  "name": "Search → Summarise",
  "description": "Runs a web search and summarises results",
  "agent_ids": ["<search-agent-id>", "<summarise-agent-id>"],
  "workflow_type": "sequential"
}
```

### Conditional example
```json
{
  "name": "Sentiment Pipeline",
  "description": "Escalates on negative sentiment",
  "agent_ids": ["<sentiment-agent-id>", "<escalation-agent-id>"],
  "workflow_type": "conditional",
  "conditions": { "<escalation-agent-id>": "sentiment == 'negative'" }
}
```
""",
    response_model=WorkflowOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Workflow created"},
        400: {"description": "One or more agent_ids do not belong to the caller"},
    },
)
def create_workflow(
    data: CreateWorkflowRequest,
    user_id: str = Depends(get_current_user_id),
) -> WorkflowOut:
    """Create and persist a new workflow for the authenticated user."""
    return workflow_service.create_workflow(data, user_id)


# ---------------------------------------------------------------------------
# GET /workflows  — list all workflows
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="List all workflows for the current user",
    description="""
## List workflows

Returns every workflow owned by the authenticated user.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{
  "workflows": [ { ...WorkflowOut... } ],
  "total": 2
}
```
""",
    response_model=WorkflowListOut,
    status_code=status.HTTP_200_OK,
)
def list_workflows(
    user_id: str = Depends(get_current_user_id),
) -> WorkflowListOut:
    """Return all workflows belonging to the authenticated user."""
    workflows = workflow_service.list_workflows(user_id)
    return WorkflowListOut(workflows=workflows, total=len(workflows))


# ---------------------------------------------------------------------------
# GET /workflows/{workflow_id}  — get one workflow
# ---------------------------------------------------------------------------

@router.get(
    "/{workflow_id}",
    summary="Get a single workflow by ID",
    description="""
## Get workflow

Fetches a single workflow by its UUID.

### Authentication
Requires the ``X-User-ID`` header.  The workflow must belong to the caller.

### Response
Returns a full ``WorkflowOut`` document.
""",
    response_model=WorkflowOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Workflow found"},
        404: {"description": "Workflow not found or belongs to a different user"},
    },
)
def get_workflow(
    workflow_id: str = Path(..., description="UUID of the workflow to retrieve"),
    user_id: str = Depends(get_current_user_id),
) -> WorkflowOut:
    """Fetch a single workflow by ID for the authenticated user."""
    return workflow_service.get_workflow(workflow_id, user_id)


# ---------------------------------------------------------------------------
# PUT /workflows/{workflow_id}  — update a workflow
# ---------------------------------------------------------------------------

@router.put(
    "/{workflow_id}",
    summary="Update an existing workflow",
    description="""
## Update workflow

Partially patches an existing workflow.  Only supplied fields are updated.

### Authentication
Requires the ``X-User-ID`` header.

### Example
```json
{
  "agent_ids": ["<agent-a>", "<agent-b>", "<agent-c>"],
  "workflow_type": "parallel",
  "parallel_groups": [["<agent-a>", "<agent-b>"]]
}
```
""",
    response_model=WorkflowOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Workflow updated"},
        404: {"description": "Workflow not found"},
    },
)
def update_workflow(
    data: UpdateWorkflowRequest,
    workflow_id: str = Path(..., description="UUID of the workflow to update"),
    user_id: str = Depends(get_current_user_id),
) -> WorkflowOut:
    """Patch an existing workflow with the supplied fields."""
    return workflow_service.update_workflow(workflow_id, user_id, data)


# ---------------------------------------------------------------------------
# DELETE /workflows/{workflow_id}  — delete a workflow
# ---------------------------------------------------------------------------

@router.delete(
    "/{workflow_id}",
    summary="Delete a workflow",
    description="""
## Delete workflow

Permanently removes a workflow definition from MongoDB.

> **Warning** — any custom router that references this workflow will lose
> the binding.  Update those routers before deleting.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{ "deleted": true, "workflow_id": "<uuid>" }
```
""",
    response_model=WorkflowDeleteOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Workflow deleted"},
        404: {"description": "Workflow not found"},
    },
)
def delete_workflow(
    workflow_id: str = Path(..., description="UUID of the workflow to delete"),
    user_id: str = Depends(get_current_user_id),
) -> WorkflowDeleteOut:
    """Delete a workflow by ID."""
    return workflow_service.delete_workflow(workflow_id, user_id)
