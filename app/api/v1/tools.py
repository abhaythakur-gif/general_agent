from fastapi import APIRouter
from app.tools.registry import list_tools
from app.llm.provider import list_models
from app.schemas.response import ToolsListResponse, ModelsListResponse

router = APIRouter(tags=["Tools & Models"])


@router.get("/tools", summary="List all available tools", response_model=ToolsListResponse,
            responses={200: {"description": "All tools grouped by category — no auth required"}})
def get_tools():
    """Returns every tool registered in `app/tools/registry.py`. No auth needed."""
    tools = list_tools()
    grouped = {}
    for t in tools:
        cat = t.get("category", "Other")
        grouped.setdefault(cat, []).append(t)
    return {"tools": tools, "grouped": grouped, "total": len(tools)}


@router.get("/models", summary="List all supported LLM models", response_model=ModelsListResponse,
            responses={200: {"description": "Available LLM models — no auth required"}})
def get_models():
    """Returns all LLM models available. No auth needed."""
    return {"models": list_models()}
