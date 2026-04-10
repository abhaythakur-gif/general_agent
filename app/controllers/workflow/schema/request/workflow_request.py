"""
app/controllers/workflow/schema/request/workflow_request.py
============================================================
Pydantic request schemas for the Workflow controller.

A *workflow* links one or more *agents* together and defines how data
flows between them.  Three execution strategies are supported:

| ``workflow_type`` | Behaviour |
|-------------------|-----------|
| ``sequential``    | Agents run one after the other; output of step N feeds step N+1 |
| ``conditional``   | Each agent is guarded by a Python-evaluable condition expression |
| ``parallel``      | Named groups of agents run concurrently; results are merged |
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class CreateWorkflowRequest(BaseModel):
    """
    Request body for **POST /workflows**.

    ### Required fields
    | Field         | Description                                  |
    |---------------|----------------------------------------------|
    | ``name``      | Display name of the workflow                 |
    | ``description`` | Purpose of the workflow; shown in /docs UI |

    ### Optional fields
    | Field              | Default          | Description                                      |
    |--------------------|------------------|--------------------------------------------------|
    | ``agent_ids``      | ``[]``           | Ordered list of agent UUIDs                      |
    | ``workflow_type``  | ``"sequential"`` | sequential / conditional / parallel |
    | ``conditions``     | ``{}``           | Map of agent_id → Python condition string        |
    | ``parallel_groups``| ``[]``           | List of agent-id groups that run concurrently    |

    ### Sequential example
    ```json
    {
      "name": "Search → Summarise",
      "description": "Searches the web then summarises the top results",
      "agent_ids": ["<search-agent-id>", "<summarise-agent-id>"],
      "workflow_type": "sequential"
    }
    ```

    ### Conditional example
    ```json
    {
      "name": "Sentiment Pipeline",
      "description": "Analyses sentiment and routes to the escalation agent when negative",
      "agent_ids": ["<sentiment-agent-id>", "<escalation-agent-id>"],
      "workflow_type": "conditional",
      "conditions": {
        "<escalation-agent-id>": "sentiment == 'negative'"
      }
    }
    ```

    ### Parallel example
    ```json
    {
      "name": "Multi-Source Research",
      "description": "Runs three research agents in parallel then merges results",
      "agent_ids": ["<agent-a>", "<agent-b>", "<agent-c>", "<merge-agent>"],
      "workflow_type": "parallel",
      "parallel_groups": [["<agent-a>", "<agent-b>", "<agent-c>"]]
    }
    ```
    """

    name: str = Field(..., min_length=1, description="Display name of the workflow")
    description: str = Field(..., min_length=1, description="Purpose and context of the workflow")
    agent_ids: List[str] = Field(
        default_factory=list,
        description="Ordered list of agent UUIDs to include in this workflow",
    )
    workflow_type: str = Field(
        "sequential",
        description="Execution strategy: sequential | conditional | parallel",
    )
    conditions: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Used with workflow_type='conditional'. "
            "Map of agent_id → Python expression evaluated against the shared state. "
            "The agent runs only when the expression evaluates to True."
        ),
    )
    parallel_groups: List[List[str]] = Field(
        default_factory=list,
        description=(
            "Used with workflow_type='parallel'. "
            "Each inner list is a group of agent_ids that execute concurrently."
        ),
    )


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

class UpdateWorkflowRequest(BaseModel):
    """
    Request body for **PUT /workflows/{workflow_id}**.

    All fields are optional — only provided fields are patched.

    ### Example
    ```json
    {
      "name": "Improved Sentiment Pipeline",
      "conditions": {
        "<escalation-agent-id>": "sentiment in ['negative', 'neutral']"
      }
    }
    ```
    """

    name: Optional[str] = Field(None, description="New display name")
    description: Optional[str] = Field(None, description="New description")
    agent_ids: Optional[List[str]] = Field(None, description="Replacement ordered agent list")
    workflow_type: Optional[str] = Field(None, description="New execution strategy")
    conditions: Optional[Dict[str, str]] = Field(None, description="Replacement condition map")
    parallel_groups: Optional[List[List[str]]] = Field(None, description="Replacement parallel groups")
