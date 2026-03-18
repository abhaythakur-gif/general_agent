"""
app/agentic/base/capabilities.py
----------------------------------
Enum of agent capabilities used by the decision engine to route requests.
"""

from enum import Enum


class AgentCapability(str, Enum):
    REASONING     = "reasoning"       # LLM-powered reasoning
    DETERMINISTIC = "deterministic"   # Rule/tool-chain, no LLM reasoning
    DATA_COLLECTOR = "data_collector" # Gathers missing fields from user
    AGGREGATOR    = "aggregator"      # Combines upstream agent outputs
    WORKFLOW      = "workflow"        # Orchestrates multi-step workflow
