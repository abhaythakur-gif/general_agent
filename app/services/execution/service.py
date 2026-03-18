"""
app/services/execution/service.py
-----------------------------------
Workflow execution business logic — loads workflow+agents, runs engine, persists result.
Replaces app/services/execution_service.py.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories.mongodb.workflow_repo import WorkflowRepository
from app.repositories.mongodb.agent_repo import AgentRepository
from app.repositories.mongodb.execution_repo import ExecutionRepository
from app.models.domain.agent import AgentDefinition, FieldSchema
from app.agentic.agents.workflow_runner.agent import start_workflow, resume_workflow

_wf_repo    = WorkflowRepository()
_agent_repo = AgentRepository()
_exec_repo  = ExecutionRepository()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_agent_def(doc: dict) -> AgentDefinition:
    doc["input_schema"]  = [FieldSchema(**f) for f in doc.get("input_schema", [])]
    doc["output_schema"] = [FieldSchema(**f) for f in doc.get("output_schema", [])]
    return AgentDefinition(**doc)


def execute_workflow(workflow_id: str, initial_inputs: dict, user_id: str) -> dict:
    wf = _wf_repo.get(workflow_id, user_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    conditions = wf.get("conditions", {})
    agent_defs = []
    for aid in wf.get("agent_ids", []):
        doc = _agent_repo.get_any(aid)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Agent '{aid}' referenced in workflow not found")
        agent_def = _build_agent_def(doc)
        if aid in conditions:
            agent_def.run_if = conditions[aid]
        agent_defs.append(agent_def)

    exec_id = str(uuid.uuid4())
    _exec_repo.save({
        "id": exec_id, "workflow_id": workflow_id, "user_id": user_id,
        "status": "running", "started_at": _now(), "completed_at": None,
        "log_entries": [], "final_output": None, "error_message": None,
    })

    def log_callback(entry: dict):
        _exec_repo.append_log_entry(exec_id, entry)

    try:
        result = start_workflow(
            agent_defs=agent_defs,
            initial_inputs=initial_inputs,
            workflow_id=workflow_id,
            parallel_groups=wf.get("parallel_groups", []),
            log_callback=log_callback,
        )
    except Exception as exc:
        _exec_repo.update(exec_id, {"status": "failed", "error_message": str(exc), "completed_at": _now()})
        raise HTTPException(status_code=500, detail=str(exc))

    if result["status"] == "completed":
        _exec_repo.update(exec_id, {"status": "completed", "final_output": result["state"], "completed_at": _now()})
    elif result["status"] == "paused":
        _exec_repo.update(exec_id, {"status": "paused"})
    else:
        _exec_repo.update(exec_id, {"status": "failed", "error_message": result.get("error", "Unknown"), "completed_at": _now()})

    return {
        "execution_id":       exec_id,
        "status":             result["status"],
        "final_output":       result["state"],
        "follow_up_question": result.get("follow_up_question"),
        "paused_at_agent":    result.get("paused_at_agent"),
        "missing_fields":     result.get("missing_fields", []),
    }


def resume_execution(execution_id: str, user_input: str) -> dict:
    collected: list = []

    def log_callback(entry: dict):
        collected.append(entry)
        _exec_repo.append_log_entry(execution_id, entry)

    try:
        result = resume_workflow(execution_id=execution_id, user_input=user_input, log_callback=log_callback)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if result["status"] == "completed":
        _exec_repo.update(execution_id, {"status": "completed", "final_output": result["state"], "completed_at": _now()})
    elif result["status"] == "paused":
        _exec_repo.update(execution_id, {"status": "paused"})

    return {
        "execution_id":       result["execution_id"],
        "status":             result["status"],
        "final_output":       result["state"],
        "follow_up_question": result.get("follow_up_question"),
        "paused_at_agent":    result.get("paused_at_agent"),
        "missing_fields":     result.get("missing_fields", []),
    }


def get_execution(execution_id: str) -> dict:
    doc = _exec_repo.get(execution_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    return doc


def get_execution_logs(execution_id: str) -> dict:
    doc = _exec_repo.get(execution_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    return {
        "execution_id":  execution_id,
        "status":        doc.get("status"),
        "started_at":    doc.get("started_at"),
        "completed_at":  doc.get("completed_at"),
        "log_entries":   doc.get("log_entries", []),
        "error_message": doc.get("error_message"),
    }


def list_executions(user_id: str) -> list:
    return _exec_repo.list_by_user(user_id)
