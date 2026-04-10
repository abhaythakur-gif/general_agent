"""
app/agentic/base/agent.py
--------------------------
Abstract base class every concrete agent must extend.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseAgent(ABC):
    """Every agent specialisation (reasoning, deterministic, workflow_runner) extends this."""

    @abstractmethod
    def run(self, agent_def, workflow_state: dict, log_callback: Optional[Callable] = None) -> dict:
        """
        Execute the agent against the current workflow state.
        Returns a dict of {output_variable: value} to be merged into workflow state.
        """
