"""
app/controllers/schema/request_schema/agent.py
------------------------------------------------
Request body schemas for agent endpoints.
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime


class FieldSchema(BaseModel):
    name: str
    type: str = "str"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[str]] = None


class AgentCreate(BaseModel):
    name: str
    description: str
    agent_type: str = "reasoning"
    behavior: str = "task_executor"
    llm_model: Optional[str] = "gpt-4"
    tools: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    input_schema:  List[FieldSchema] = []
    output_schema: List[FieldSchema] = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    behavior: Optional[str] = None
    llm_model: Optional[str] = None
    tools: Optional[List[str]] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    input_schema:  Optional[List[FieldSchema]] = None
    output_schema: Optional[List[FieldSchema]] = None
