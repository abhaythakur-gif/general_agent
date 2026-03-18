"""
app/config/llm/models.py
-------------------------
Pydantic schema for the LLM configuration block.
"""

from typing import Optional
from pydantic import BaseModel


class LLMModelConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    description: str = ""
