"""
app/services/agent_service.py
------------------------------
Agent business logic — wraps AgentRepository.
"""

from fastapi import HTTPException
from app.repositories.repositories import AgentRepository
from app.schemas.agent import AgentCreate, AgentUpdate

_repo = AgentRepository()


def create_agent(data: AgentCreate, user_id: str) -> dict:
    payload = data.dict()
    payload["input_schema"]  = [f.dict() for f in data.input_schema]
    payload["output_schema"] = [f.dict() for f in data.output_schema]
    return _repo.save(payload, user_id)


def list_agents(user_id: str) -> list:
    return _repo.list_by_user(user_id)


def get_agent(agent_id: str, user_id: str) -> dict:
    agent = _repo.get(agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return agent


def update_agent(agent_id: str, user_id: str, data: AgentUpdate) -> dict:
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if "input_schema" in updates and updates["input_schema"]:
        updates["input_schema"] = [f.dict() if hasattr(f, "dict") else f for f in updates["input_schema"]]
    if "output_schema" in updates and updates["output_schema"]:
        updates["output_schema"] = [f.dict() if hasattr(f, "dict") else f for f in updates["output_schema"]]
    result = _repo.update(agent_id, user_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return result


def delete_agent(agent_id: str, user_id: str) -> dict:
    deleted = _repo.delete(agent_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"deleted": True, "agent_id": agent_id}
