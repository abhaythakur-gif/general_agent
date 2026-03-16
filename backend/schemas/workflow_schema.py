from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime


class WorkflowDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_ids: List[str] = []           # ordered list of agent IDs
    workflow_type: str = "sequential"  # "sequential" | "conditional"
    conditions: Dict[str, str] = {}    # {agent_id: expression_string}
    # Each inner list is a group of agent_ids that should run in parallel
    parallel_groups: List[List[str]] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowCreate(BaseModel):
    name: str
    description: str
    agent_ids: List[str] = []
    workflow_type: str = "sequential"
    conditions: Dict[str, str] = {}
    parallel_groups: List[List[str]] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_ids: Optional[List[str]] = None
    workflow_type: Optional[str] = None
    conditions: Optional[Dict[str, str]] = None
    parallel_groups: Optional[List[List[str]]] = None


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


# ─── Execution State (for pause/resume) ──────────────────────────────────────

class ExecutionState(BaseModel):
    """
    Persisted state for a running or paused workflow execution.
    Enables mid-pipeline human-in-the-loop interactions.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: str = "running"             # running | paused | completed | failed
    current_step: int = 0               # index of the step that paused/is running
    paused_agent_name: Optional[str] = None
    follow_up_question: Optional[str] = None
    missing_fields: List[str] = []
    state: Dict[str, Any] = {}          # full workflow state at pause time
    agent_defs_raw: List[dict] = []     # serialized AgentDefinition list
    parallel_groups: List[List[str]] = []
    log_entries: List[dict] = []
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
