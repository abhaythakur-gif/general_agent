import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")
WORKFLOWS_FILE = os.path.join(DATA_DIR, "workflows.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read(filepath: str) -> list:
    _ensure_data_dir()
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)


def _write(filepath: str, data: list):
    _ensure_data_dir()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


# ─── AGENTS ──────────────────────────────────────────────────────────────────

def save_agent(agent: dict) -> dict:
    agents = _read(AGENTS_FILE)
    agent["id"] = str(uuid.uuid4())
    agent["created_at"] = datetime.utcnow().isoformat()
    agents.append(agent)
    _write(AGENTS_FILE, agents)
    return agent


def list_agents() -> list:
    return _read(AGENTS_FILE)


def get_agent(agent_id: str) -> dict | None:
    return next((a for a in _read(AGENTS_FILE) if a["id"] == agent_id), None)


def delete_agent(agent_id: str):
    agents = [a for a in _read(AGENTS_FILE) if a["id"] != agent_id]
    _write(AGENTS_FILE, agents)


# ─── WORKFLOWS ───────────────────────────────────────────────────────────────

def save_workflow(workflow: dict) -> dict:
    workflows = _read(WORKFLOWS_FILE)
    workflow["id"] = str(uuid.uuid4())
    workflow["created_at"] = datetime.utcnow().isoformat()
    workflows.append(workflow)
    _write(WORKFLOWS_FILE, workflows)
    return workflow


def list_workflows() -> list:
    return _read(WORKFLOWS_FILE)


def get_workflow(workflow_id: str) -> dict | None:
    return next((w for w in _read(WORKFLOWS_FILE) if w["id"] == workflow_id), None)


def delete_workflow(workflow_id: str):
    workflows = [w for w in _read(WORKFLOWS_FILE) if w["id"] != workflow_id]
    _write(WORKFLOWS_FILE, workflows)
