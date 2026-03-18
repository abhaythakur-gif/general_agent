"""
app/models/domain/workflow.py
------------------------------
Pure business/domain objects for Workflows and Executions.
DB-agnostic — no MongoDB-specific fields.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class WorkflowDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_ids: List[str] = []
    workflow_type: str = "sequential"
    conditions: Dict[str, str] = {}
    parallel_groups: List[List[str]] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExecutionLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    status: str = "running"
    log_entries: List[dict] = []
    final_output: Optional[dict] = None
    error_message: Optional[str] = None


class ExecutionState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: str = "running"
    current_step: int = 0
    paused_agent_name: Optional[str] = None
    follow_up_question: Optional[str] = None
    missing_fields: List[str] = []
    state: Dict[str, Any] = {}
    agent_defs_raw: List[dict] = []
