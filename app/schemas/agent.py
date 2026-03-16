from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from typing import List
import uuid
from datetime import datetime


class FieldSchema(BaseModel):
    name: str
    type: str = "str"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[str]] = None


class AgentDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    run_if: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator("input_schema", always=True, pre=False)
    def _fill_input_schema(cls, v, values):
        if not v:
            return [FieldSchema(name=n.strip()) for n in values.get("inputs", []) if n.strip()]
        return v

    @validator("output_schema", always=True, pre=False)
    def _fill_output_schema(cls, v, values):
        if not v:
            return [FieldSchema(name=n.strip()) for n in values.get("outputs", []) if n.strip()]
        return v

    @property
    def effective_inputs(self) -> List[str]:
        return [f.name for f in self.input_schema] if self.input_schema else list(self.inputs)

    @property
    def effective_outputs(self) -> List[str]:
        return [f.name for f in self.output_schema] if self.output_schema else list(self.outputs)


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
