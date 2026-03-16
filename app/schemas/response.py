from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class UserInitResponse(BaseModel):
    user_id: str
    is_new: bool


class UserProfileResponse(BaseModel):
    user_id: str
    created_at: str
    last_seen_at: str


class FieldSchemaResponse(BaseModel):
    name: str
    type: str = "str"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[str]] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    agent_type: str
    behavior: str
    llm_model: Optional[str] = None
    tools: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    input_schema: List[FieldSchemaResponse] = []
    output_schema: List[FieldSchemaResponse] = []
    run_if: Optional[str] = None
    user_id: str
    created_at: str


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


class AgentDeleteResponse(BaseModel):
    deleted: bool
    agent_id: str


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    agent_ids: List[str] = []
    workflow_type: str = "sequential"
    conditions: Dict[str, str] = {}
    parallel_groups: List[List[str]] = []
    user_id: str
    created_at: str


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int


class WorkflowDeleteResponse(BaseModel):
    deleted: bool
    workflow_id: str


class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    final_output: Optional[Dict[str, Any]] = None
    follow_up_question: Optional[str] = None
    paused_at_agent: Optional[str] = None
    missing_fields: List[str] = []


class ExecutionDetailResponse(BaseModel):
    id: str
    workflow_id: str
    user_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    log_entries: List[Dict[str, Any]] = []


class ExecutionLogsResponse(BaseModel):
    execution_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    log_entries: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


class ExecutionListResponse(BaseModel):
    executions: List[ExecutionDetailResponse]
    total: int


class ToolsListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    grouped: Dict[str, List[Dict[str, Any]]]
    total: int


class ModelsListResponse(BaseModel):
    models: List[Any]


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    message: str
    docs: str
    version: str
