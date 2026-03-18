"""
app/config/tools/models.py
---------------------------
Pydantic schema for a single tool's configuration entry.
"""

from typing import List, Optional
from pydantic import BaseModel


class ToolConfig(BaseModel):
    name: str
    description: str = ""
    inputs: List[str] = []
    category: str = "Other"
    api_source: str = ""
    enabled: bool = True
    requires_key: Optional[str] = None
