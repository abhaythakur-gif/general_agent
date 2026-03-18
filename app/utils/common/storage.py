"""
app/utils/common/storage.py
-----------------------------
Thin façade over MongoDB repositories — stateless helper functions only.
Provides a single import point for all persistence operations used by
the agentic engine and tool registry.

Import new repository classes from the new locations.
"""

from typing import Optional

from app.repositories.mongodb.agent_repo import AgentRepository
from app.repositories.mongodb.workflow_repo import WorkflowRepository
from app.repositories.mongodb.execution_repo import ExecutionRepository
from app.repositories.mongodb.tool_repo import ToolRepository
from app.repositories.mongodb.custom_router_repo import CustomRouterRepository

_agents     = AgentRepository()
_workflows  = WorkflowRepository()
_executions = ExecutionRepository()
_tools      = ToolRepository()
_routers    = CustomRouterRepository()

_ANON = "__anonymous__"


# ─── AGENTS ──────────────────────────────────────────────────────────────────

def save_agent(agent: dict, user_id: str = _ANON) -> dict:
    return _agents.save(agent, user_id)


def list_agents(user_id: str = _ANON) -> list:
    return _agents.list_by_user(user_id)


def get_agent(agent_id: str, user_id: Optional[str] = None) -> dict | None:
    if user_id:
        return _agents.get(agent_id, user_id)
    return _agents.get_any(agent_id)


def delete_agent(agent_id: str, user_id: str = _ANON):
    _agents.delete(agent_id, user_id)


# ─── WORKFLOWS ───────────────────────────────────────────────────────────────

def save_workflow(workflow: dict, user_id: str = _ANON) -> dict:
    return _workflows.save(workflow, user_id)


def list_workflows(user_id: str = _ANON) -> list:
    return _workflows.list_by_user(user_id)


def get_workflow(workflow_id: str, user_id: Optional[str] = None) -> dict | None:
    return _workflows.get(workflow_id, user_id)


def delete_workflow(workflow_id: str, user_id: str = _ANON):
    _workflows.delete(workflow_id, user_id)


def update_workflow(workflow_id: str, updates: dict, user_id: str = _ANON) -> dict | None:
    return _workflows.update(workflow_id, user_id, updates)


# ─── EXECUTIONS ──────────────────────────────────────────────────────────────

def save_execution(execution: dict) -> dict:
    return _executions.save(execution)


def get_execution(execution_id: str) -> dict | None:
    return _executions.get(execution_id)


def update_execution(execution_id: str, updates: dict) -> dict | None:
    return _executions.update(execution_id, updates)


def list_executions(user_id: str = _ANON) -> list:
    return _executions.list_by_user(user_id)


# ─── TOOLS ───────────────────────────────────────────────────────────────────

def seed_tools(tools: list) -> None:
    _tools.seed(tools)


def list_tools() -> list:
    return _tools.list_all()


def get_tool_meta(name: str) -> Optional[dict]:
    return _tools.get(name)


# ─── CUSTOM ROUTERS ──────────────────────────────────────────────────────────

def save_custom_router(router: dict, user_id: str = _ANON) -> dict:
    return _routers.save(router, user_id)


def list_custom_routers(user_id: str = _ANON) -> list:
    return _routers.list_by_user(user_id)


def get_custom_router(router_id: str, user_id: str = _ANON) -> Optional[dict]:
    return _routers.get(router_id, user_id)


def update_custom_router(router_id: str, updates: dict, user_id: str = _ANON) -> Optional[dict]:
    return _routers.update(router_id, user_id, updates)


def delete_custom_router(router_id: str, user_id: str = _ANON) -> bool:
    return _routers.delete(router_id, user_id)


def router_name_exists(user_id: str, name: str, exclude_id: Optional[str] = None) -> bool:
    return _routers.name_exists(user_id, name, exclude_id)
