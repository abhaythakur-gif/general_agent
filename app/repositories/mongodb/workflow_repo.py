"""
app/repositories/mongodb/workflow_repo.py
------------------------------------------
MongoDB repository for the 'workflows' collection.
"""

import uuid
from typing import Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import BaseMongoRepository, _now, _strip_mongo


class WorkflowRepository(BaseMongoRepository):

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
        query: dict = {"_id": workflow_id}
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
