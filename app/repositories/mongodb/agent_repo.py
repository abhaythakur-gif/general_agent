"""
app/repositories/mongodb/agent_repo.py
----------------------------------------
MongoDB repository for the 'agents' collection.
"""

import uuid
from typing import Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import BaseMongoRepository, _now, _strip_mongo


class AgentRepository(BaseMongoRepository):

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
        """Get an agent without user_id scoping (used by execution service)."""
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
