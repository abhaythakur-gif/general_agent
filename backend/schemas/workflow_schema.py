from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


class WorkflowDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_ids: List[str] = []   # ordered list of agent IDs
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowCreate(BaseModel):
    name: str
    description: str
    agent_ids: List[str] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_ids: Optional[List[str]] = None


class ExecutionRequest(BaseModel):
    initial_inputs: dict = {}


class ExecutionLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    status: str = "running"   # running | completed | failed
    log_entries: List[dict] = []
    final_output: Optional[dict] = None
    error_message: Optional[str] = None
