"""
app/repositories/repositories.py
----------------------------------
Repository classes for every MongoDB collection.
All write/read operations are scoped by user_id.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db.mongo import get_mongo_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_mongo(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d


# ─── Agent Repository ─────────────────────────────────────────────────────────

class AgentRepository:

    def __init__(self):
        self._col = get_mongo_db()["agents"]

    def save(self, agent: dict, user_id: str) -> dict:
        doc = dict(agent)
        doc["id"] = str(uuid.uuid4())
        doc["_id"] = doc["id"]
        doc["user_id"] = user_id
        doc["created_at"] = _now()
        self._col.insert_one(doc)
        return _strip_mongo(doc)

    def list_by_user(self, user_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"user_id": user_id})]

    def get(self, agent_id: str, user_id: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": agent_id, "user_id": user_id})
        return _strip_mongo(doc) if doc else None

    def get_any(self, agent_id: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": agent_id})
        return _strip_mongo(doc) if doc else None

    def update(self, agent_id: str, user_id: str, updates: dict) -> Optional[dict]:
        updates.pop("_id", None)
        updates.pop("id", None)
        updates.pop("user_id", None)
        result = self._col.find_one_and_update(
            {"_id": agent_id, "user_id": user_id},
            {"$set": updates},
            return_document=True,
        )
        return _strip_mongo(result) if result else None

    def delete(self, agent_id: str, user_id: str) -> bool:
        result = self._col.delete_one({"_id": agent_id, "user_id": user_id})
        return result.deleted_count > 0


# ─── Workflow Repository ──────────────────────────────────────────────────────

class WorkflowRepository:

    def __init__(self):
        self._col = get_mongo_db()["workflows"]

    def save(self, workflow: dict, user_id: str) -> dict:
        doc = dict(workflow)
        doc["id"] = str(uuid.uuid4())
        doc["_id"] = doc["id"]
        doc["user_id"] = user_id
        doc["created_at"] = _now()
        self._col.insert_one(doc)
        return _strip_mongo(doc)

    def list_by_user(self, user_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"user_id": user_id})]

    def get(self, workflow_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        query = {"_id": workflow_id}
        if user_id:
            query["user_id"] = user_id
        doc = self._col.find_one(query)
        return _strip_mongo(doc) if doc else None

    def update(self, workflow_id: str, user_id: str, updates: dict) -> Optional[dict]:
        updates.pop("_id", None)
        updates.pop("id", None)
        updates.pop("user_id", None)
        result = self._col.find_one_and_update(
            {"_id": workflow_id, "user_id": user_id},
            {"$set": updates},
            return_document=True,
        )
        return _strip_mongo(result) if result else None

    def delete(self, workflow_id: str, user_id: str) -> bool:
        result = self._col.delete_one({"_id": workflow_id, "user_id": user_id})
        return result.deleted_count > 0


# ─── Execution Repository ─────────────────────────────────────────────────────

class ExecutionRepository:

    def __init__(self):
        self._col = get_mongo_db()["execution_logs"]

    def save(self, execution: dict) -> dict:
        doc = dict(execution)
        doc["_id"] = doc["id"]
        self._col.insert_one(doc)
        return _strip_mongo(doc)

    def get(self, execution_id: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": execution_id})
        return _strip_mongo(doc) if doc else None

    def update(self, execution_id: str, updates: dict) -> Optional[dict]:
        updates.pop("_id", None)
        updates.pop("id", None)
        updates["updated_at"] = _now()
        result = self._col.find_one_and_update(
            {"_id": execution_id},
            {"$set": updates},
            return_document=True,
        )
        return _strip_mongo(result) if result else None

    def append_log_entry(self, execution_id: str, entry: dict) -> None:
        self._col.update_one({"_id": execution_id}, {"$push": {"log_entries": entry}})

    def list_by_user(self, user_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"user_id": user_id})]

    def list_by_workflow(self, workflow_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"workflow_id": workflow_id})]


# ─── Tool Repository ──────────────────────────────────────────────────────────

class ToolRepository:
    """
    Stores tool metadata in the 'tools' collection.
    Tools are global (not user-scoped); _id is the tool name.
    """

    def __init__(self):
        self._col = get_mongo_db()["tools"]

    def seed(self, tools: list) -> None:
        """Upsert every tool by name. Safe to call on every startup."""
        for t in tools:
            doc = dict(t)
            doc["_id"] = doc["name"]          # tool name is the primary key
            self._col.update_one(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True,
            )

    def list_all(self) -> list:
        """Return all tools sorted by category."""
        return [
            _strip_mongo(d)
            for d in self._col.find({}).sort("category", 1)
        ]

    def get(self, name: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": name})
        return _strip_mongo(doc) if doc else None
