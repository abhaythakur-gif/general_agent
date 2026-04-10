"""
app/controllers/agent/agent_controller.py
==========================================
FastAPI router that handles all **Agent** HTTP endpoints.

Design principles
-----------------
* **Controller** — responsible only for HTTP ingress/egress: validation,
  status codes, response serialisation.  All business logic lives in
  ``app.services.agent_service``.
* Every route declares ``response_model`` so FastAPI strips internal
  fields from the outbound JSON automatically.
* Detailed ``summary``, ``description``, and ``responses`` blocks are
  surfaced directly in the **/docs** Swagger UI.

Authentication
--------------
All routes require the ``X-User-ID`` header.  The dependency
``get_current_user_id`` raises ``HTTP 401`` when the header is absent.

Prefix
------
All routes are mounted at ``/api/v1/agents`` via ``main.py``.
"""

from fastapi import APIRouter, Depends, Path, status

from app.controllers.agent.schema.request.agent_request import (
    CreateAgentRequest,
    UpdateAgentRequest,
)
from app.controllers.agent.schema.response.agent_response import (
    AgentDeleteOut,
    AgentListOut,
    AgentOut,
)
from app.services.auth.service import get_current_user_id
from app.services.agents import service as agent_service

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        401: {"description": "X-User-ID header is missing"},
        422: {"description": "Request body failed Pydantic validation"},
    },
)


# ---------------------------------------------------------------------------
# POST /agents  — create a new agent
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="Create a new agent",
    description="""
## Create a new agent

Persists a new agent definition to MongoDB and returns the created document.

### Authentication
Requires the ``X-User-ID`` header.

### Agent types
| Value | Meaning |
|-------|---------|
| ``reasoning`` | Uses chain-of-thought to break down tasks |
| ``planner`` | Builds a step-by-step plan before acting |
| ``executor`` | Directly invokes tools without extra reasoning |

### Behaviour classes
| Value | Meaning |
|-------|---------|
| ``task_executor`` | Runs a task and returns a result |
| ``data_transformer`` | Transforms structured data from one format to another |
| ``qa`` | Answers questions given a context |

### Minimal example
```json
{
  "name": "Sentiment Analyser",
  "description": "Classifies text as positive, negative, or neutral"
}
```

### Full example
```json
{
  "name": "Sentiment Analyser",
  "description": "Classifies text sentiment using zero-shot reasoning",
  "agent_type": "reasoning",
  "behavior": "task_executor",
  "llm_model": "gpt-4",
  "tools": [],
  "input_schema": [
    {"name": "text", "type": "str", "required": true, "description": "Text to classify"}
  ],
  "output_schema": [
    {
      "name": "sentiment",
      "type": "str",
      "allowed_values": ["positive", "negative", "neutral"],
      "required": true
    }
  ]
}
```
""",
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Agent created successfully"},
        400: {"description": "Validation error — bad field types / values"},
    },
)
def create_agent(
    data: CreateAgentRequest,
    user_id: str = Depends(get_current_user_id),
) -> AgentOut:
    """Create and persist a new agent for the authenticated user."""
    return agent_service.create_agent(data, user_id)


# ---------------------------------------------------------------------------
# GET /agents  — list all agents
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="List all agents for the current user",
    description="""
## List agents

Returns every agent owned by the authenticated user.

### Authentication
Requires the ``X-User-ID`` header.

### Response
```json
{
  "agents": [ { ...AgentOut... } ],
  "total": 3
}
```
""",
    response_model=AgentListOut,
    status_code=status.HTTP_200_OK,
    responses={200: {"description": "List of agents (may be empty)"}},
)
def list_agents(
    user_id: str = Depends(get_current_user_id),
) -> AgentListOut:
    """Return all agents belonging to the authenticated user."""
    agents = agent_service.list_agents(user_id)
    return AgentListOut(agents=agents, total=len(agents))


# ---------------------------------------------------------------------------
# GET /agents/{agent_id}  — get a single agent
# ---------------------------------------------------------------------------

@router.get(
    "/{agent_id}",
    summary="Get a single agent by ID",
    description="""
## Get agent

Fetches a single agent by its UUID.

### Authentication
Requires the ``X-User-ID`` header.  The agent must belong to the caller.

### Path parameter
| Parameter  | Description |
|------------|-------------|
| ``agent_id`` | UUID of the agent returned at creation time |

### Response
Returns a full ``AgentOut`` document on success.
""",
    response_model=AgentOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Agent found"},
        404: {"description": "Agent not found or belongs to a different user"},
    },
)
def get_agent(
    agent_id: str = Path(..., description="UUID of the agent to retrieve"),
    user_id: str = Depends(get_current_user_id),
) -> AgentOut:
    """Fetch a single agent by ID for the authenticated user."""
    return agent_service.get_agent(agent_id, user_id)


# ---------------------------------------------------------------------------
# PUT /agents/{agent_id}  — update an agent
# ---------------------------------------------------------------------------

@router.put(
    "/{agent_id}",
    summary="Update an existing agent",
    description="""
## Update agent

Partially patches an existing agent.  Only the fields supplied in the
request body are updated; all others remain unchanged.

### Authentication
Requires the ``X-User-ID`` header.  The agent must belong to the caller.

### Partial update example
```json
{
  "llm_model": "gpt-4o",
  "tools": ["web_search", "weather"]
}
```

### Full replacement example
```json
{
  "name": "Advanced Sentiment Analyser",
  "description": "Uses CoT to detect nuanced sentiment",
  "agent_type": "reasoning",
  "behavior": "qa",
  "llm_model": "gpt-4o",
  "tools": [],
  "input_schema": [{"name": "text", "type": "str", "required": true}],
  "output_schema": [{"name": "sentiment", "type": "str"}]
}
```
""",
    response_model=AgentOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Agent updated"},
        404: {"description": "Agent not found"},
    },
)
def update_agent(
    data: UpdateAgentRequest,
    agent_id: str = Path(..., description="UUID of the agent to update"),
    user_id: str = Depends(get_current_user_id),
) -> AgentOut:
    """Patch an existing agent with the supplied fields."""
    return agent_service.update_agent(agent_id, user_id, data)


# ---------------------------------------------------------------------------
# DELETE /agents/{agent_id}  — delete an agent
# ---------------------------------------------------------------------------

@router.delete(
    "/{agent_id}",
    summary="Delete an agent",
    description="""
## Delete agent

Permanently removes an agent from MongoDB.

> **Warning** — any workflow that references this agent will fail to
> execute after deletion.  Remove or update those workflows first.

### Authentication
Requires the ``X-User-ID`` header.  The agent must belong to the caller.

### Response
```json
{ "deleted": true, "agent_id": "<uuid>" }
```
""",
    response_model=AgentDeleteOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Agent deleted"},
        404: {"description": "Agent not found"},
    },
)
def delete_agent(
    agent_id: str = Path(..., description="UUID of the agent to delete"),
    user_id: str = Depends(get_current_user_id),
) -> AgentDeleteOut:
    """Delete an agent by ID."""
    return agent_service.delete_agent(agent_id, user_id)
