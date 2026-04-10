"""
app/controllers/router/schema/request/router_request.py
========================================================
Pydantic request schemas for the Custom Router controller.

A *custom router* is a named collection of workflows.  When a user
sends a natural-language query to the router it uses an LLM to select
the most relevant workflow and executes it automatically.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class CreateRouterRequest(BaseModel):
    """
    Request body for **POST /routers**.

    ### Required fields
    | Field    | Description                             |
    |----------|-----------------------------------------|
    | ``name`` | Display name of the router              |

    ### Optional fields
    | Field            | Default | Description                                            |
    |------------------|---------|--------------------------------------------------------|
    | ``description``  | ``""``  | What kinds of queries this router handles              |
    | ``workflow_ids`` | ``[]``  | Workflows the router can dispatch to (deduplication applied) |

    ### Example
    ```json
    {
      "name": "General Assistant Router",
      "description": "Routes queries to travel, weather, or sentiment workflows",
      "workflow_ids": ["<travel-wf-id>", "<weather-wf-id>", "<sentiment-wf-id>"]
    }
    ```
    """

    name: str = Field(..., min_length=1, description="Display name of the custom router")
    description: str = Field("", description="What kinds of queries this router handles")
    workflow_ids: List[str] = Field(
        default_factory=list,
        description="Workflow UUIDs this router can dispatch to",
    )

    @validator("workflow_ids")
    def deduplicate(cls, v: List[str]) -> List[str]:  # noqa: N805
        seen: List[str] = []
        for item in v:
            if item not in seen:
                seen.append(item)
        return seen


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

class UpdateRouterRequest(BaseModel):
    """
    Request body for **PUT /routers/{router_id}**.

    All fields are optional — only supplied fields are patched.

    ### Example
    ```json
    { "workflow_ids": ["<travel-wf-id>", "<news-wf-id>"] }
    ```
    """

    name: Optional[str] = Field(None, description="New display name")
    description: Optional[str] = Field(None, description="New description")
    workflow_ids: Optional[List[str]] = Field(None, description="Replacement workflow list")

    @validator("workflow_ids", pre=True, always=True)
    def deduplicate(cls, v: Optional[List[str]]) -> Optional[List[str]]:  # noqa: N805
        if v is None:
            return v
        seen: List[str] = []
        for item in v:
            if item not in seen:
                seen.append(item)
        return seen


# ---------------------------------------------------------------------------
# DISPATCH
# ---------------------------------------------------------------------------

class RouterDispatchRequest(BaseModel):
    """
    Request body for **POST /routers/{router_id}/dispatch**.

    Sends a natural-language query to the router.  The router uses an
    LLM to select the best matching workflow and executes it.

    ### Example
    ```json
    {
      "query": "What is the weather like in London tomorrow?",
      "initial_inputs": { "date": "tomorrow" }
    }
    ```
    """

    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language query used to select the best workflow",
    )
    initial_inputs: dict = Field(
        default_factory=dict,
        description="Optional extra key/value pairs merged into the workflow's initial inputs",
    )
