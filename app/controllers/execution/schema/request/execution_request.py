"""
app/controllers/execution/schema/request/execution_request.py
=============================================================
Pydantic request schemas for the Execution controller.

Executions are created by triggering a workflow and may be resumed when
an agent requires additional user input mid-run.
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# EXECUTE
# ---------------------------------------------------------------------------

class ExecuteWorkflowRequest(BaseModel):
    """
    Request body for **POST /workflows/{workflow_id}/execute**.

    ### Field guide
    | Field             | Description                                              |
    |-------------------|----------------------------------------------------------|
    | ``initial_inputs`` | Key/value pairs seeded into the shared workflow state before the first agent runs |

    The keys must match the ``input_schema`` field names of the *first*
    agent in the workflow.

    ### Example — text analysis workflow
    ```json
    {
      "initial_inputs": {
        "text": "I absolutely love this product, it exceeded all my expectations!"
      }
    }
    ```

    ### Example — travel planning workflow
    ```json
    {
      "initial_inputs": {
        "origin": "New York",
        "destination": "Paris",
        "departure_date": "2026-06-01"
      }
    }
    ```
    """

    initial_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Key/value pairs seeded into the shared workflow state before execution begins. "
            "Keys should match the first agent's input_schema field names."
        ),
    )


# ---------------------------------------------------------------------------
# RESUME
# ---------------------------------------------------------------------------

class ResumeExecutionRequest(BaseModel):
    """
    Request body for **POST /executions/{execution_id}/resume**.

    When an agent detects that required information is missing it pauses
    the execution and returns a ``follow_up_question``.  The caller must
    answer that question here to continue the run.

    ### Example
    ```json
    {
      "user_input": "My departure date is June 1st 2026"
    }
    ```
    """

    user_input: str = Field(
        ...,
        min_length=1,
        description="The user's answer to the follow_up_question returned in the paused execution",
    )
