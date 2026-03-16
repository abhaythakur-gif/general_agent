"""
app/services/workflow_service.py
---------------------------------
Workflow business logic — wraps WorkflowRepository.
"""

from fastapi import HTTPException
from app.repositories.repositories import WorkflowRepository, AgentRepository
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate

_repo       = WorkflowRepository()
_agent_repo = AgentRepository()


def _verify_agents(agent_ids: list) -> None:
    missing = [aid for aid in agent_ids if not _agent_repo.get_any(aid)]
    if missing:
        raise HTTPException(status_code=400, detail=f"The following agent_ids do not exist: {missing}")


def create_workflow(data: WorkflowCreate, user_id: str) -> dict:
    if data.agent_ids:
        _verify_agents(data.agent_ids)
    return _repo.save(data.dict(), user_id)


def list_workflows(user_id: str) -> list:
    return _repo.list_by_user(user_id)


def get_workflow(workflow_id: str, user_id: str) -> dict:
    wf = _repo.get(workflow_id, user_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf


def update_workflow(workflow_id: str, user_id: str, data: WorkflowUpdate) -> dict:
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if "agent_ids" in updates and updates["agent_ids"]:
        _verify_agents(updates["agent_ids"])
    result = _repo.update(workflow_id, user_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return result


def delete_workflow(workflow_id: str, user_id: str) -> dict:
    deleted = _repo.delete(workflow_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return {"deleted": True, "workflow_id": workflow_id}
