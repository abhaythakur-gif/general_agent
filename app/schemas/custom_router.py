from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime


class CustomRouterDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    user_id: str = ""
    workflow_ids: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator("workflow_ids")
    def deduplicate_workflow_ids(cls, v):  # noqa: N805
        seen = []
        for item in v:
            if item not in seen:
                seen.append(item)
        return seen


class CustomRouterCreate(BaseModel):
    name: str
    description: str = ""
    workflow_ids: List[str] = []

    @validator("workflow_ids")
    def deduplicate_workflow_ids(cls, v):  # noqa: N805
        seen = []
        for item in v:
            if item not in seen:
                seen.append(item)
        return seen


class CustomRouterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workflow_ids: Optional[List[str]] = None

    @validator("workflow_ids", pre=True, always=True)
    def deduplicate_workflow_ids(cls, v):  # noqa: N805
        if v is None:
            return v
        seen = []
        for item in v:
            if item not in seen:
                seen.append(item)
        return seen
