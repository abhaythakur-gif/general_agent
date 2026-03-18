"""
app/agentic/base/agent_result.py
---------------------------------
Typed result returned by every agent's run() method.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentResult(BaseModel):
    status: str                         # "completed" | "paused" | "failed"
    outputs: Dict[str, Any] = {}        # Output variable values
    follow_up_question: Optional[str] = None
    missing_fields: List[str] = []
    error: Optional[str] = None
