"""
app/controllers/schema/request_schema/workflow.py
---------------------------------------------------
Request body schemas for workflow endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


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
