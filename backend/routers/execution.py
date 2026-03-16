from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from database.crud import (
    get_workflow, get_agent, create_execution_log,
    append_log_entry, complete_execution, fail_execution, get_execution_log
)
from backend.schemas.workflow_schema import ExecutionRequest
from backend.schemas.agent_schema import AgentDefinition
from workflow.workflow_runner import start_workflow, resume_workflow
import threading

router = APIRouter(tags=["Execution"])

# In-memory store for streaming logs during active executions
_active_logs: dict = {}


@router.post("/workflows/{workflow_id}/execute")
def execute_workflow(
    workflow_id: str,
    request: ExecutionRequest,
    db: Session = Depends(get_db),
):
    wf = get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Load all agents in order
    agent_defs = []
    for agent_id in wf.agent_ids:
        agent_row = get_agent(db, agent_id)
        if not agent_row:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_id}' referenced in workflow not found"
            )
        agent_defs.append(
            AgentDefinition(
                id=agent_row.id,
                name=agent_row.name,
                description=agent_row.description,
                agent_type=agent_row.agent_type,
                behavior=getattr(agent_row, "behavior", "task_executor") or "task_executor",
                llm_model=agent_row.llm_model,
                tools=agent_row.tools or [],
                inputs=agent_row.inputs or [],
                outputs=agent_row.outputs or [],
                input_schema=getattr(agent_row, "input_schema", []) or [],
                output_schema=getattr(agent_row, "output_schema", []) or [],
            )
        )

    parallel_groups = getattr(wf, "parallel_groups", []) or []

    # Create execution log entry
    exec_log = create_execution_log(db, workflow_id)
    exec_id  = exec_log.id
    _active_logs[exec_id] = []

    def log_callback(entry: dict):
        _active_logs[exec_id].append(entry)
        append_log_entry(db, exec_id, entry)

    # Run workflow synchronously (blocking)
    try:
        result = start_workflow(
            agent_defs=agent_defs,
            initial_inputs=request.initial_inputs,
            workflow_id=workflow_id,
            parallel_groups=parallel_groups,
            log_callback=log_callback,
        )
        if result["status"] == "completed":
            complete_execution(db, exec_id, result["state"])
        return {
            "execution_id":       result["execution_id"],
            "status":             result["status"],
            "final_output":       result["state"],
            "follow_up_question": result.get("follow_up_question"),
            "paused_at_agent":    result.get("paused_at_agent"),
            "missing_fields":     result.get("missing_fields", []),
            "logs":               _active_logs.get(exec_id, []),
        }
    except Exception as e:
        fail_execution(db, exec_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _active_logs.pop(exec_id, None)


class ResumeRequest(BaseModel):
    user_input: str


@router.post("/executions/{execution_id}/resume")
def resume_execution(execution_id: str, request: ResumeRequest):
    """Resume a paused workflow execution with new user input."""
    collected: list = []

    def log_callback(entry: dict):
        collected.append(entry)

    try:
        result = resume_workflow(
            execution_id=execution_id,
            user_input=request.user_input,
            log_callback=log_callback,
        )
        return {
            "execution_id":       result["execution_id"],
            "status":             result["status"],
            "final_output":       result["state"],
            "follow_up_question": result.get("follow_up_question"),
            "paused_at_agent":    result.get("paused_at_agent"),
            "missing_fields":     result.get("missing_fields", []),
            "logs":               collected,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/logs")
def get_logs(execution_id: str, db: Session = Depends(get_db)):
    log = get_execution_log(db, execution_id)
    if not log:
        raise HTTPException(status_code=404, detail="Execution log not found")
    return {
        "execution_id": execution_id,
        "status": log.status,
        "started_at": log.started_at,
        "completed_at": log.completed_at,
        "log_entries": log.log_entries,
        "error_message": log.error_message,
    }


@router.get("/executions/{execution_id}/output")
def get_output(execution_id: str, db: Session = Depends(get_db)):
    log = get_execution_log(db, execution_id)
    if not log:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        "execution_id": execution_id,
        "status": log.status,
        "final_output": log.final_output,
        "error_message": log.error_message,
    }
