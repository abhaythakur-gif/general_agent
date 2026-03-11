from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.crud import (
    get_workflow, get_agent, create_execution_log,
    append_log_entry, complete_execution, fail_execution, get_execution_log
)
from backend.schemas.workflow_schema import ExecutionRequest
from backend.schemas.agent_schema import AgentDefinition
from workflow.workflow_runner import run_workflow
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
                llm_model=agent_row.llm_model,
                tools=agent_row.tools or [],
                inputs=agent_row.inputs or [],
                outputs=agent_row.outputs or [],
            )
        )

    # Create execution log entry
    exec_log = create_execution_log(db, workflow_id)
    exec_id = exec_log.id
    _active_logs[exec_id] = []

    def log_callback(entry: dict):
        _active_logs[exec_id].append(entry)
        append_log_entry(db, exec_id, entry)

    # Run workflow synchronously (blocking)
    try:
        final_state = run_workflow(
            agent_defs=agent_defs,
            initial_inputs=request.initial_inputs,
            log_callback=log_callback,
        )
        complete_execution(db, exec_id, final_state)
        return {
            "execution_id": exec_id,
            "status": "completed",
            "final_output": final_state,
            "logs": _active_logs.get(exec_id, []),
        }
    except Exception as e:
        fail_execution(db, exec_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _active_logs.pop(exec_id, None)


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
