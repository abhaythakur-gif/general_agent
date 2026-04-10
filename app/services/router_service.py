"""
app/services/router_service.py
================================
Business logic for the Custom Router resource.

A custom router is a named set of workflows.  When a query is dispatched
to it the service uses an LLM to pick the best-matching workflow and
triggers an execution.

Functions
---------
- create_router   — persist a new router
- list_routers    — list all routers for a user
- get_router      — fetch one router by ID
- update_router   — patch a router
- delete_router   — remove a router
- dispatch_router — route a NL query to the best workflow and execute it
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.repositories.mongodb.custom_router_repo import CustomRouterRepository
from app.repositories.mongodb.workflow_repo import WorkflowRepository
from app.services.execution import service as execution_service
from app.llm.provider import get_llm

_repo: CustomRouterRepository = CustomRouterRepository()
_wf_repo: WorkflowRepository = WorkflowRepository()

_ROUTER_LLM: str = os.getenv("SMART_ROUTER_LLM", "gpt-4")


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_router(data: dict, user_id: str) -> dict:
    """Persist a new custom router.  ``data`` must have ``name``."""
    return _repo.save(data, user_id)


def list_routers(user_id: str) -> List[dict]:
    """Return all custom routers owned by *user_id*."""
    return _repo.list_by_user(user_id)


def get_router(router_id: str, user_id: str) -> dict:
    """Fetch a single router; raises 404 when not found."""
    doc = _repo.get(router_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Router '{router_id}' not found")
    return doc


def update_router(router_id: str, user_id: str, updates: dict) -> dict:
    """Patch a router; raises 404 when not found."""
    result = _repo.update(router_id, user_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Router '{router_id}' not found")
    return result


def delete_router(router_id: str, user_id: str) -> dict:
    """Delete a router; raises 404 when not found."""
    ok = _repo.delete(router_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Router '{router_id}' not found")
    return {"deleted": True, "router_id": router_id}


# ---------------------------------------------------------------------------
# Dispatch (LLM-powered routing)
# ---------------------------------------------------------------------------

def dispatch_router(
    router_id: str,
    user_id: str,
    query: str,
    initial_inputs: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Route a natural-language *query* to the best matching workflow and
    execute it synchronously.

    Returns a dict compatible with ``RouterDispatchOut``.

    Algorithm
    ---------
    1. Load the router and fetch all its linked workflow docs.
    2. Build a prompt listing each workflow's name and description.
    3. Ask the LLM to respond with the single best-matching workflow ID.
    4. Validate the response, then trigger an execution.
    5. Return the execution result together with the selected workflow ID.
    """
    router = get_router(router_id, user_id)
    workflow_ids: List[str] = router.get("workflow_ids", [])

    if not workflow_ids:
        return {
            "selected_workflow_id": None,
            "execution_id": None,
            "status": "failed",
            "error": "This router has no linked workflows.",
        }

    # Fetch workflow metadata (name + description)
    wf_list: List[dict] = []
    for wid in workflow_ids:
        wf = _wf_repo.get(wid, user_id)
        if wf:
            wf_list.append(wf)

    if not wf_list:
        return {
            "selected_workflow_id": None,
            "execution_id": None,
            "status": "failed",
            "error": "None of the linked workflows were found.",
        }

    # Build LLM routing prompt
    wf_text = "\n".join(
        f"{i + 1}. ID: {wf['id']} | Name: {wf['name']} | "
        f"Description: {wf.get('description', 'No description')}"
        for i, wf in enumerate(wf_list)
    )
    prompt = (
        "You are a workflow routing assistant.\n"
        "Based on the user's query, select the single most relevant workflow.\n\n"
        f"User Query: {query}\n\n"
        f"Available Workflows:\n{wf_text}\n\n"
        "Respond with ONLY the exact workflow ID (UUID). "
        "No explanation, punctuation, or extra text."
    )

    try:
        llm = get_llm(_ROUTER_LLM)
        response = llm.invoke(prompt)
        matched_id: str = response.content.strip().strip('"').strip("'")
    except Exception as exc:
        return {
            "selected_workflow_id": None,
            "execution_id": None,
            "status": "failed",
            "error": f"LLM routing error: {exc}",
        }

    # Validate the LLM's choice
    valid_ids = {wf["id"]: wf for wf in wf_list}
    if matched_id not in valid_ids:
        # Fallback: prefix match
        matched_id = next(
            (wid for wid in valid_ids if wid.startswith(matched_id[:8])),
            None,
        )

    if not matched_id:
        return {
            "selected_workflow_id": None,
            "execution_id": None,
            "status": "failed",
            "error": "LLM returned an invalid workflow ID.",
        }

    # Execute the selected workflow
    try:
        result = execution_service.execute_workflow(
            workflow_id=matched_id,
            initial_inputs={**(initial_inputs or {}), "query": query},
            user_id=user_id,
        )
        return {
            "selected_workflow_id": matched_id,
            "execution_id": result.get("execution_id") if isinstance(result, dict) else getattr(result, "execution_id", None),
            "status": result.get("status") if isinstance(result, dict) else getattr(result, "status", "unknown"),
            "final_output": result.get("final_output") if isinstance(result, dict) else getattr(result, "final_output", None),
            "follow_up_question": result.get("follow_up_question") if isinstance(result, dict) else getattr(result, "follow_up_question", None),
            "missing_fields": result.get("missing_fields", []) if isinstance(result, dict) else getattr(result, "missing_fields", []),
        }
    except HTTPException as exc:
        return {
            "selected_workflow_id": matched_id,
            "execution_id": None,
            "status": "failed",
            "error": exc.detail,
        }
    except Exception as exc:
        return {
            "selected_workflow_id": matched_id,
            "execution_id": None,
            "status": "failed",
            "error": str(exc),
        }
