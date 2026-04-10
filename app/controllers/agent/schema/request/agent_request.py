"""
app/controllers/agent/schema/request/agent_request.py
======================================================
Pydantic request schemas for the Agent controller.

Every schema documented here is used exactly once — as the request body
of the corresponding FastAPI endpoint — so any change here automatically
updates the /docs UI, the OpenAPI JSON, and client-side validation.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared building block
# ---------------------------------------------------------------------------

class FieldSchemaRequest(BaseModel):
    """
    Describes a single input or output field for an agent.

    - ``name``          – machine-readable field identifier (e.g. ``"query"``).
    - ``type``          – Python type hint as a string (``"str"``, ``"int"``, ``"list"`` …).
    - ``description``   – human-readable explanation shown in the /docs UI.
    - ``required``      – whether the caller *must* supply this field.
    - ``default``       – value used when the field is absent from the payload.
    - ``allowed_values``– optional enum; the LLM will be instructed to pick only
                          from this list.
    """

    name: str = Field(..., min_length=1, description="Machine-readable field identifier")
    type: str = Field("str", description="Python type hint string, e.g. 'str', 'int', 'list'")
    description: str = Field("", description="Human-readable explanation of the field")
    required: bool = Field(True, description="Whether the caller must supply this field")
    default: Optional[Any] = Field(None, description="Value used when field is absent")
    allowed_values: Optional[List[str]] = Field(
        None, description="Restrict LLM output to one of these values (enum-like)"
    )


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class CreateAgentRequest(BaseModel):
    """
    Request body for **POST /agents**.

    ### Required fields
    | Field        | Description                                           |
    |--------------|-------------------------------------------------------|
    | ``name``     | Display name of the agent (e.g. *"Sentiment Analyser"*) |
    | ``description`` | What this agent does; fed to the LLM as system context |

    ### Optional fields
    | Field           | Default         | Description                                   |
    |-----------------|-----------------|-----------------------------------------------|
    | ``agent_type``  | ``"reasoning"`` | One of ``reasoning``, ``planner``, ``executor`` |
    | ``behavior``    | ``"task_executor"`` | One of ``task_executor``, ``data_transformer``, ``qa`` |
    | ``llm_model``   | ``"gpt-4"``     | Model identifier returned by ``GET /models``  |
    | ``tools``       | ``[]``          | Tool names returned by ``GET /tools``         |
    | ``input_schema``  | ``[]``        | Typed input fields; auto-derived from ``inputs`` if empty |
    | ``output_schema`` | ``[]``        | Typed output fields; auto-derived from ``outputs`` if empty |

    ### Example
    ```json
    {
      "name": "Sentiment Analyser",
      "description": "Classifies text as positive, negative, or neutral",
      "agent_type": "reasoning",
      "behavior": "task_executor",
      "llm_model": "gpt-4",
      "tools": [],
      "input_schema": [
        {"name": "text", "type": "str", "required": true}
      ],
      "output_schema": [
        {"name": "sentiment", "type": "str", "allowed_values": ["positive", "negative", "neutral"]}
      ]
    }
    ```
    """

    name: str = Field(..., min_length=1, description="Display name of the agent")
    description: str = Field(..., min_length=1, description="What this agent does; used as LLM system prompt context")
    agent_type: str = Field(
        "reasoning",
        description="Agent reasoning strategy. One of: reasoning | planner | executor",
    )
    behavior: str = Field(
        "task_executor",
        description="High-level behaviour class. One of: task_executor | data_transformer | qa",
    )
    llm_model: Optional[str] = Field(
        "gpt-4",
        description="LLM model identifier (see GET /models for valid values)",
    )
    tools: List[str] = Field(
        default_factory=list,
        description="List of tool names to attach (see GET /tools for valid values)",
    )
    inputs: List[str] = Field(
        default_factory=list,
        description="Shorthand input field names — used when input_schema is empty",
    )
    outputs: List[str] = Field(
        default_factory=list,
        description="Shorthand output field names — used when output_schema is empty",
    )
    input_schema: List[FieldSchemaRequest] = Field(
        default_factory=list,
        description="Typed input field definitions; takes precedence over 'inputs'",
    )
    output_schema: List[FieldSchemaRequest] = Field(
        default_factory=list,
        description="Typed output field definitions; takes precedence over 'outputs'",
    )


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

class UpdateAgentRequest(BaseModel):
    """
    Request body for **PUT /agents/{agent_id}**.

    All fields are optional — only the supplied fields are patched.

    ### Example (partial update)
    ```json
    {
      "llm_model": "gpt-4o",
      "tools": ["web_search", "weather"]
    }
    ```
    """

    name: Optional[str] = Field(None, description="New display name")
    description: Optional[str] = Field(None, description="New description / system-prompt context")
    agent_type: Optional[str] = Field(None, description="New agent type (reasoning | planner | executor)")
    behavior: Optional[str] = Field(None, description="New behaviour class")
    llm_model: Optional[str] = Field(None, description="New LLM model identifier")
    tools: Optional[List[str]] = Field(None, description="Replacement tool list")
    inputs: Optional[List[str]] = Field(None, description="Replacement shorthand input names")
    outputs: Optional[List[str]] = Field(None, description="Replacement shorthand output names")
    input_schema: Optional[List[FieldSchemaRequest]] = Field(None, description="Replacement typed input fields")
    output_schema: Optional[List[FieldSchemaRequest]] = Field(None, description="Replacement typed output fields")
