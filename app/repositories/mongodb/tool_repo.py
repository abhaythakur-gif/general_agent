"""
app/repositories/mongodb/tool_repo.py
---------------------------------------
MongoDB repository for the 'tools' collection.
Tools are global (not user-scoped); the tool name is the primary key.
"""

from typing import List, Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import _strip_mongo


class ToolRepository:
    """
    Stores tool metadata in the 'tools' collection.
    Tools are global — not user-scoped; _id is the tool name.
    """

    def __init__(self):
        self._col = get_mongo_db()["tools"]

    def seed(self, tools: List[dict]) -> None:
        """Upsert every tool by name. Safe to call on every startup."""
        for t in tools:
            doc = dict(t)
            doc["_id"] = doc["name"]
            self._col.update_one(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True,
            )

    def list_all(self) -> List[dict]:
        """Return all tools sorted by category."""
        return [_strip_mongo(d) for d in self._col.find({}).sort("category", 1)]

    def get(self, name: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": name})
        return _strip_mongo(doc) if doc else None
