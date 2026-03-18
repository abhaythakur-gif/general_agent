"""
app/repositories/mongodb/execution_repo.py
-------------------------------------------
MongoDB repository for the 'execution_logs' collection.
"""

from typing import Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import BaseMongoRepository, _now, _strip_mongo


class ExecutionRepository(BaseMongoRepository):

    def __init__(self):
        self._col = get_mongo_db()["execution_logs"]

    def save(self, execution: dict, *args, **kwargs) -> dict:
        doc = dict(execution)
        doc["_id"] = doc["id"]
        self._col.insert_one(doc)
        return _strip_mongo(doc)

    def list_by_user(self, user_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"user_id": user_id})]

    def get(self, execution_id: str, *args, **kwargs) -> Optional[dict]:
        doc = self._col.find_one({"_id": execution_id})
        return _strip_mongo(doc) if doc else None

    def update(self, execution_id: str, updates: dict, *args, **kwargs) -> Optional[dict]:
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

    def list_by_workflow(self, workflow_id: str) -> list:
        return [_strip_mongo(d) for d in self._col.find({"workflow_id": workflow_id})]

    def delete(self, execution_id: str, *args, **kwargs) -> bool:
        result = self._col.delete_one({"_id": execution_id})
        return result.deleted_count > 0
