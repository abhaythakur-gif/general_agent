from fastapi import APIRouter
from tools.tool_registry import list_tools
from llm.llm_provider import list_models

router = APIRouter(tags=["Tools"])


@router.get("/tools")
def get_tools():
    """Return all available tools with metadata grouped by category."""
    tools = list_tools()
    grouped = {}
    for t in tools:
        cat = t.get("category", "Other")
        grouped.setdefault(cat, []).append(t)
    return {"tools": tools, "grouped": grouped, "total": len(tools)}


@router.get("/models")
def get_models():
    """Return all supported LLM models."""
    return {"models": list_models()}
