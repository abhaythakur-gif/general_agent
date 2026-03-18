"""
app/repositories/mongodb/chat_repo.py
---------------------------------------
MongoDB repository for 'chat_sessions' and 'chat_messages' collections.
All operations are scoped by user_id; tenant_id is a human-readable label.
"""

import uuid
from typing import List, Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import _now, _strip_mongo


class ChatRepository:

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

    def list_sessions(self, user_id: str) -> List[dict]:
        return [
            _strip_mongo(d)
            for d in self._sessions.find({"user_id": user_id}).sort("last_message_at", -1)
        ]

    def get_session(self, session_id: str, user_id: str) -> Optional[dict]:
        doc = self._sessions.find_one({"_id": session_id, "user_id": user_id})
        return _strip_mongo(doc) if doc else None

    def get_session_by_tenant(self, user_id: str, tenant_id: str) -> Optional[dict]:
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
        role: str,
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

    def get_messages(self, session_id: str, user_id: str, limit: int = 30) -> List[dict]:
        cursor = (
            self._messages.find({"session_id": session_id, "user_id": user_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        docs = list(cursor)
        docs.reverse()
        return [_strip_mongo(d) for d in docs]

    def clear_messages(self, session_id: str, user_id: str) -> int:
        result = self._messages.delete_many({"session_id": session_id, "user_id": user_id})
        self._sessions.update_one(
            {"_id": session_id, "user_id": user_id},
            {"$set": {"message_count": 0}},
        )
        return result.deleted_count
