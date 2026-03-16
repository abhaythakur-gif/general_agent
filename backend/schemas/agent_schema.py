from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any
import uuid
from datetime import datetime


# ─── Field Schema ─────────────────────────────────────────────────────────────

class FieldSchema(BaseModel):
    """
    Rich schema definition for a single input or output field.
    Carries name, type, description, required flag, and optional default value.
    """
    name: str
    type: str = "str"          # str | int | float | bool | list | dict
    description: str = ""
    required: bool = True
    default: Optional[Any] = None


# ─── Agent Definition ─────────────────────────────────────────────────────────

class AgentDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_type: str = "reasoning"       # deterministic | reasoning | hybrid
    behavior: str = "task_executor"     # task_executor | data_collector | aggregator
    llm_model: Optional[str] = "gpt-4"
    tools: List[str] = []

    # ── Legacy flat lists (backward compat — honoured when *_schema is empty) ─
    inputs: List[str] = []
    outputs: List[str] = []

    # ── Rich typed schemas (preferred over flat lists) ────────────────────────
    input_schema:  List[FieldSchema] = []
    output_schema: List[FieldSchema] = []

    run_if: Optional[str] = None        # condition expression; None means always run
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # ── Auto-populate schemas from legacy flat lists on load ──────────────────
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

    # ── Convenience helpers ───────────────────────────────────────────────────
    @property
    def effective_inputs(self) -> List[str]:
        """Flat list of input variable names (from schema or legacy list)."""
        return [f.name for f in self.input_schema] if self.input_schema else list(self.inputs)

    @property
    def effective_outputs(self) -> List[str]:
        """Flat list of output variable names (from schema or legacy list)."""
        return [f.name for f in self.output_schema] if self.output_schema else list(self.outputs)


# ─── Create / Update DTOs ─────────────────────────────────────────────────────

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
