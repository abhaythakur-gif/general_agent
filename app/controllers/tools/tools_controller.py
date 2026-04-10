"""
app/controllers/tools/tools_controller.py
==========================================
FastAPI router that handles all **Tools & Models** HTTP endpoints.

Design principles
-----------------
* **Controller** — thin HTTP layer; no business logic.
* Both endpoints are **public** (no ``X-User-ID`` required) because
  the tool and model catalogues are read-only platform metadata.
* Tool data is seeded from ``app/tools/registry.py`` on startup.
* Model data is read from ``app/llm/provider.py``.

Prefix
------
Routes are mounted at ``/api/v1`` in ``main.py`` (i.e.
``GET /api/v1/tools`` and ``GET /api/v1/models``).
"""

from fastapi import APIRouter, status

from app.controllers.tools.schema.response.tools_response import (
    ModelsListOut,
    ToolsListOut,
)
from app.llm.provider import list_models
from app.tools.registry import list_tools

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    tags=["Tools & Models"],
)


# ---------------------------------------------------------------------------
# GET /tools  — list all available tools
# ---------------------------------------------------------------------------

@router.get(
    "/tools",
    summary="List all available tools",
    description="""
## List tools

Returns every tool registered in the platform, both as a flat list and
grouped by category.

### No auth required

### Tool object shape
```json
{
  "name": "web_search",
  "category": "Search",
  "description": "Search the web via SerpAPI",
  "parameters": ["query"]
}
```

### Grouped response shape
```json
{
  "tools": [ { ...tool... } ],
  "grouped": {
    "Search":  [ { ...tool... } ],
    "Weather": [ { ...tool... } ],
    "Travel":  [ { ...tool... } ]
  },
  "total": 8
}
```

### When to use this
Call this endpoint to populate the tool selector when building an agent
via ``POST /agents``. Pass the ``name`` values in the ``tools`` field of
``CreateAgentRequest``.
""",
    response_model=ToolsListOut,
    status_code=status.HTTP_200_OK,
    responses={200: {"description": "All registered tools"}},
)
def get_tools() -> ToolsListOut:
    """Return all platform tools, flat and grouped by category."""
    tools = list_tools()
    grouped: dict = {}
    for t in tools:
        cat = t.get("category", "Other")
        grouped.setdefault(cat, []).append(t)
    return ToolsListOut(tools=tools, grouped=grouped, total=len(tools))


# ---------------------------------------------------------------------------
# GET /models  — list all supported LLM models
# ---------------------------------------------------------------------------

@router.get(
    "/models",
    summary="List all supported LLM models",
    description="""
## List LLM models

Returns all LLM models available in the platform.

### No auth required

### Model object shape
```json
{ "id": "gpt-4", "provider": "openai", "description": "OpenAI GPT-4" }
```

### When to use this
Call this endpoint to populate the model selector when creating or
updating an agent.  Pass the ``id`` value in the ``llm_model`` field of
``CreateAgentRequest``.
""",
    response_model=ModelsListOut,
    status_code=status.HTTP_200_OK,
    responses={200: {"description": "All available LLM models"}},
)
def get_models() -> ModelsListOut:
    """Return all LLM models available in the platform."""
    return ModelsListOut(models=list_models())
