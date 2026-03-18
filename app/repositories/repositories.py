"""
app/repositories/repositories.py — SHIM
-------------------------------------------
Backward-compatibility shim.
All repository classes now live under app/repositories/mongodb/<entity>_repo.py.
Re-exports all classes so existing import statements continue to work.
"""

from app.repositories.mongodb.agent_repo import AgentRepository  # noqa: F401
from app.repositories.mongodb.workflow_repo import WorkflowRepository  # noqa: F401
from app.repositories.mongodb.execution_repo import ExecutionRepository  # noqa: F401
from app.repositories.mongodb.tool_repo import ToolRepository  # noqa: F401
from app.repositories.mongodb.chat_repo import ChatRepository  # noqa: F401
from app.repositories.mongodb.custom_router_repo import CustomRouterRepository  # noqa: F401

# Legacy: keep get_mongo_db importable from here as some old code used it
from resources.mongodb import get_mongo_db  # noqa: F401
