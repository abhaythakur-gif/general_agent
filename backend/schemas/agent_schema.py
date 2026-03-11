from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


class AgentDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_type: str = "reasoning"   # deterministic | reasoning | hybrid
    llm_model: Optional[str] = "gpt-4"
    tools: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentCreate(BaseModel):
    name: str
    description: str
    agent_type: str = "reasoning"
    llm_model: Optional[str] = "gpt-4"
    tools: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    llm_model: Optional[str] = None
    tools: Optional[List[str]] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
