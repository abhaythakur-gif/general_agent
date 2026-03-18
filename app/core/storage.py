"""
app/core/storage.py — SHIM
-----------------------------
Backward-compatibility shim. All real logic lives in app/utils/common/storage.py.
Re-exports every function so existing UI pages and API code continue to work.
"""

# Re-export the full public API from the new canonical location.
from app.utils.common.storage import (  # noqa: F401
    save_agent, list_agents, get_agent, delete_agent,
    save_workflow, list_workflows, get_workflow, delete_workflow, update_workflow,
    save_execution, get_execution, update_execution, list_executions,
    seed_tools, list_tools, get_tool_meta,
    save_custom_router, list_custom_routers, get_custom_router,
    update_custom_router, delete_custom_router, router_name_exists,
)

# Also re-export repo classes for any code that imports them directly from here.
from app.repositories.mongodb.agent_repo import AgentRepository  # noqa: F401
from app.repositories.mongodb.workflow_repo import WorkflowRepository  # noqa: F401
from app.repositories.mongodb.execution_repo import ExecutionRepository  # noqa: F401
from app.repositories.mongodb.tool_repo import ToolRepository  # noqa: F401
from app.repositories.mongodb.custom_router_repo import CustomRouterRepository  # noqa: F401
