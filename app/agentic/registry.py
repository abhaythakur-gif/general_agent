"""
app/agentic/registry.py
------------------------
Maps agent_type string → agent class or builder function.
Extend this when adding new agent types.
"""

from app.agentic.factory import build_agent  # noqa: F401 — re-exported for callers

# Runtime registry: agent_type string → builder callable
# The builder pattern (factory function) is used rather than class instantiation
# because agents are stateless per-run.
AGENT_REGISTRY: dict = {
    "reasoning":      build_agent,   # LLM-powered tool-using agent
    "deterministic":  build_agent,   # Rule/tool-chain agent (no LLM reasoning)
}


def get_builder(agent_type: str):
    """Return the builder function for the given agent_type string."""
    builder = AGENT_REGISTRY.get(agent_type)
    if builder is None:
        # Graceful fallback to reasoning
        return AGENT_REGISTRY["reasoning"]
    return builder
