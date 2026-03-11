from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.crud import (
    create_agent, get_agent, list_agents, update_agent, delete_agent
)
from backend.schemas.agent_schema import AgentCreate, AgentUpdate

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("")
def create(data: AgentCreate, db: Session = Depends(get_db)):
    return create_agent(db, data)


@router.get("")
def list_all(db: Session = Depends(get_db)):
    return list_agents(db)


@router.get("/{agent_id}")
def get_one(agent_id: str, db: Session = Depends(get_db)):
    agent = get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}")
def update(agent_id: str, data: AgentUpdate, db: Session = Depends(get_db)):
    agent = update_agent(db, agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}")
def delete(agent_id: str, db: Session = Depends(get_db)):
    success = delete_agent(db, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}
