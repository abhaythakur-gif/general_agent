"""
app/controllers/router/router_controller.py
============================================
FastAPI router (HTTP) that handles all **Custom Router** endpoints.

Design principles
-----------------
* **Controller** — validates HTTP requests, delegates to
  ``app.services.router_service``, and serialises responses.
* A *custom router* is a named collection of workflows.  The dispatch
  endpoint uses an LLM to intelligently select the best-matching
  workflow for a free-text user query.

Custom Router lifecycle
-----------------------
```
POST /routers                 → create a named router
PUT  /routers/{id}            → add/remove linked workflows
POST /routers/{id}/dispatch   → send a query; LLM picks a workflow & runs it
GET  /routers/{id}            → inspect router config
DELETE /routers/{id}          → remove router
```

Authentication
--------------
All routes require the ``X-User-ID`` header.

Prefix
------
Mounted at ``/api/v1/routers`` in ``main.py``.
"""

from fastapi import APIRouter, Depends, Path, status

from app.controllers.router.schema.request.router_request import (
    CreateRouterRequest,
    RouterDispatchRequest,
    UpdateRouterRequest,
)
from app.controllers.router.schema.response.router_response import (
    RouterDeleteOut,
    RouterDispatchOut,
    RouterListOut,
    RouterOut,
)
from app.services.auth.service import get_current_user_id
from app.services import router_service

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/routers",
    tags=["Custom Routers"],
    responses={
        401: {"description": "X-User-ID header is missing"},
        422: {"description": "Request body failed Pydantic validation"},
    },
)


# ---------------------------------------------------------------------------
# POST /routers  — create a router
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="Create a custom router",
    description="""
## Create custom router

Creates a named router that can dispatch user queries to the most
relevant linked workflow using LLM-powered semantic matching.

### Authentication
Requires the ``X-User-ID`` header.

### Example — router linked to three workflows
```json
{
  "name": "General Assistant Router",
  "description": "Handles travel, weather, and sentiment queries",
  "workflow_ids": ["<travel-wf-id>", "<weather-wf-id>", "<sentiment-wf-id>"]
}
```

### Example — empty router (add workflows later via PUT)
```json
{
  "name": "My Router",
  "description": "Will be configured after workflows are created"
}
```
""",
    response_model=RouterOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Router created"},
        400: {"description": "Validation error"},
    },
)
def create_router(
    data: CreateRouterRequest,
    user_id: str = Depends(get_current_user_id),
) -> RouterOut:
    """Create and persist a new custom router."""
    return router_service.create_router(data.dict(), user_id)


# ---------------------------------------------------------------------------
# GET /routers  — list routers
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="List all custom routers for the current user",
    description="""
## List routers

Returns every custom router owned by the authenticated user.

### Authentication
Requires the ``X-User-ID`` header.
""",
    response_model=RouterListOut,
    status_code=status.HTTP_200_OK,
)
def list_routers(
    user_id: str = Depends(get_current_user_id),
) -> RouterListOut:
    """List all custom routers for the authenticated user."""
    routers = router_service.list_routers(user_id)
    return RouterListOut(routers=routers, total=len(routers))


# ---------------------------------------------------------------------------
# GET /routers/{router_id}  — get one router
# ---------------------------------------------------------------------------

@router.get(
    "/{router_id}",
    summary="Get a custom router by ID",
    description="""
## Get router

Fetches a single custom router by its UUID.

### Authentication
Requires the ``X-User-ID`` header.
""",
    response_model=RouterOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Router found"},
        404: {"description": "Router not found"},
    },
)
def get_router(
    router_id: str = Path(..., description="UUID of the router to retrieve"),
    user_id: str = Depends(get_current_user_id),
) -> RouterOut:
    """Fetch a custom router by ID."""
    return router_service.get_router(router_id, user_id)


# ---------------------------------------------------------------------------
# PUT /routers/{router_id}  — update a router
# ---------------------------------------------------------------------------

@router.put(
    "/{router_id}",
    summary="Update a custom router",
    description="""
## Update router

Partially patches a router.  Only supplied fields are updated.

### Authentication
Requires the ``X-User-ID`` header.

### Example — add a new workflow
```json
{
  "workflow_ids": ["<travel-wf-id>", "<weather-wf-id>", "<news-wf-id>"]
}
```
""",
    response_model=RouterOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Router updated"},
        404: {"description": "Router not found"},
    },
)
def update_router(
    data: UpdateRouterRequest,
    router_id: str = Path(..., description="UUID of the router to update"),
    user_id: str = Depends(get_current_user_id),
) -> RouterOut:
    """Patch a custom router with the supplied fields."""
    updates = {k: v for k, v in data.dict().items() if v is not None}
    return router_service.update_router(router_id, user_id, updates)


# ---------------------------------------------------------------------------
# DELETE /routers/{router_id}  — delete a router
# ---------------------------------------------------------------------------

@router.delete(
    "/{router_id}",
    summary="Delete a custom router",
    description="""
## Delete router

Permanently removes a custom router from MongoDB.

### Authentication
Requires the ``X-User-ID`` header.
""",
    response_model=RouterDeleteOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Router deleted"},
        404: {"description": "Router not found"},
    },
)
def delete_router(
    router_id: str = Path(..., description="UUID of the router to delete"),
    user_id: str = Depends(get_current_user_id),
) -> RouterDeleteOut:
    """Delete a custom router by ID."""
    return router_service.delete_router(router_id, user_id)


# ---------------------------------------------------------------------------
# POST /routers/{router_id}/dispatch  — LLM dispatch
# ---------------------------------------------------------------------------

@router.post(
    "/{router_id}/dispatch",
    summary="Dispatch a query to the best matching workflow",
    description="""
## Dispatch query

Sends a natural-language query to the router.  The service:

1. Loads all linked workflows and their descriptions.
2. Prompts an LLM to select the single best-matching workflow.
3. Executes that workflow with the initial inputs.
4. Returns the execution result.

### Authentication
Requires the ``X-User-ID`` header.

### How routing works
The LLM receives a prompt like:
```
Based on the user's query, select the single most relevant workflow.

User Query: What is the weather in London tomorrow?

Available Workflows:
1. ID: <uuid> | Name: Travel Planner | Description: Plans trips and books flights
2. ID: <uuid> | Name: Weather Agent  | Description: Fetches real-time weather data
3. ID: <uuid> | Name: Sentiment Bot  | Description: Classifies text sentiment

Respond with ONLY the workflow ID.
```

### Example request
```json
{
  "query": "What's the weather in London tomorrow?",
  "initial_inputs": {}
}
```

### Example response — dispatch completed
```json
{
  "selected_workflow_id": "<weather-workflow-uuid>",
  "execution_id": "<execution-uuid>",
  "status": "completed",
  "final_output": {
    "city": "London",
    "temperature": "12°C",
    "conditions": "Cloudy with light rain"
  }
}
```

### Example response — dispatch paused
```json
{
  "selected_workflow_id": "<travel-workflow-uuid>",
  "execution_id": "<execution-uuid>",
  "status": "paused",
  "follow_up_question": "What is your departure date?",
  "missing_fields": ["departure_date"]
}
```
""",
    response_model=RouterDispatchOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Query dispatched and execution result returned"},
        404: {"description": "Router not found"},
        500: {"description": "LLM routing or execution error"},
    },
)
def dispatch_router(
    data: RouterDispatchRequest,
    router_id: str = Path(..., description="UUID of the router to dispatch through"),
    user_id: str = Depends(get_current_user_id),
) -> RouterDispatchOut:
    """Route a natural-language query to the best workflow and execute it."""
    result = router_service.dispatch_router(
        router_id=router_id,
        user_id=user_id,
        query=data.query,
        initial_inputs=data.initial_inputs,
    )
    return RouterDispatchOut(**result)
