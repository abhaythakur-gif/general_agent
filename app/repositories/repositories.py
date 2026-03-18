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


# ─── Chat Repository ──────────────────────────────────────────────────────────

class ChatRepository:
    """
    Manages chat_sessions and chat_messages collections.
    All operations are scoped by user_id; tenant_id is a human-readable label
    chosen by the user to identify (and resume) a conversation.
    """

    def __init__(self):
        db = get_mongo_db()
        self._sessions = db["chat_sessions"]
        self._messages = db["chat_messages"]

    # ── Sessions ──────────────────────────────────────────────────────────────

    def create_session(
        self,
        user_id: str,
        tenant_id: str,
        title: str = "",
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        llm_model: str = "gpt-4",
    ) -> dict:
        now = _now()
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "title": title or tenant_id,
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "llm_model": llm_model,
            "created_at": now,
            "last_message_at": now,
            "message_count": 0,
        }
        doc["_id"] = doc["id"]
        self._sessions.insert_one(doc)
        return _strip_mongo(doc)

    def list_sessions(self, user_id: str) -> list:
        """Return all sessions for a user, newest first."""
        return [
            _strip_mongo(d)
            for d in self._sessions.find(
                {"user_id": user_id}
            ).sort("last_message_at", -1)
        ]

    def get_session(self, session_id: str, user_id: str) -> Optional[dict]:
        doc = self._sessions.find_one({"_id": session_id, "user_id": user_id})
        return _strip_mongo(doc) if doc else None

    def get_session_by_tenant(self, user_id: str, tenant_id: str) -> Optional[dict]:
        """Find the most-recently-active session matching (user_id, tenant_id)."""
        doc = self._sessions.find_one(
            {"user_id": user_id, "tenant_id": tenant_id},
            sort=[("last_message_at", -1)],
        )
        return _strip_mongo(doc) if doc else None

    def delete_session(self, session_id: str, user_id: str) -> bool:
        result = self._sessions.delete_one({"_id": session_id, "user_id": user_id})
        if result.deleted_count:
            self._messages.delete_many({"session_id": session_id})
            return True
        return False

    def _touch_session(self, session_id: str) -> None:
        """Update last_message_at and increment message_count."""
        self._sessions.update_one(
            {"_id": session_id},
            {"$set": {"last_message_at": _now()}, "$inc": {"message_count": 1}},
        )

    # ── Messages ──────────────────────────────────────────────────────────────

    def save_message(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        role: str,               # "user" | "assistant"
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        now = _now()
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "metadata": metadata or {},
        }
        doc["_id"] = doc["id"]
        self._messages.insert_one(doc)
        self._touch_session(session_id)
        return _strip_mongo(doc)

    def get_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 30,
    ) -> list:
        """Return the last `limit` messages in chronological order."""
        cursor = (
            self._messages.find({"session_id": session_id, "user_id": user_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        docs = list(cursor)
        docs.reverse()
        return [_strip_mongo(d) for d in docs]

    def clear_messages(self, session_id: str, user_id: str) -> int:
        """Delete all messages in a session. Returns deleted count."""
        result = self._messages.delete_many(
            {"session_id": session_id, "user_id": user_id}
        )
        self._sessions.update_one(
            {"_id": session_id, "user_id": user_id},
            {"$set": {"message_count": 0}},
        )
        return result.deleted_count


# ─── Custom Router Repository ─────────────────────────────────────────────────

class CustomRouterRepository:
    """
    Manages the 'custom_routers' collection.
    Each document represents a user-defined named router that is scoped to
    a hand-picked subset of the user's workflows.
    """

    def __init__(self):
        self._col = get_mongo_db()["custom_routers"]

    def save(self, router: dict, user_id: str) -> dict:
        doc = dict(router)
        doc["id"] = str(uuid.uuid4())
        doc["_id"] = doc["id"]
        doc["user_id"] = user_id
        doc["created_at"] = _now()
        doc["updated_at"] = _now()
        self._col.insert_one(doc)
        return _strip_mongo(doc)

    def list_by_user(self, user_id: str) -> list:
        return [
            _strip_mongo(d)
            for d in self._col.find({"user_id": user_id}).sort("created_at", -1)
        ]

    def get(self, router_id: str, user_id: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": router_id, "user_id": user_id})
        return _strip_mongo(doc) if doc else None

    def update(self, router_id: str, user_id: str, updates: dict) -> Optional[dict]:
        updates.pop("_id", None)
        updates.pop("id", None)
        updates.pop("user_id", None)
        updates["updated_at"] = _now()
        result = self._col.find_one_and_update(
            {"_id": router_id, "user_id": user_id},
            {"$set": updates},
            return_document=True,
        )
        return _strip_mongo(result) if result else None

    def delete(self, router_id: str, user_id: str) -> bool:
        result = self._col.delete_one({"_id": router_id, "user_id": user_id})
        return result.deleted_count > 0

    def name_exists(self, user_id: str, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if a router with this name already exists for the user."""
        query: dict = {"user_id": user_id, "name": name}
        if exclude_id:
            query["_id"] = {"$ne": exclude_id}
        return self._col.count_documents(query) > 0
