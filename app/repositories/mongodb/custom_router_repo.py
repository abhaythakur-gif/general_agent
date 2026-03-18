"""
app/repositories/mongodb/custom_router_repo.py
-----------------------------------------------
MongoDB repository for the 'custom_routers' collection.
"""

import uuid
from typing import List, Optional

from resources.mongodb import get_mongo_db
from app.repositories.mongodb.base import BaseMongoRepository, _now, _strip_mongo


class CustomRouterRepository(BaseMongoRepository):

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

    def list_by_user(self, user_id: str) -> List[dict]:
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
        query: dict = {"user_id": user_id, "name": name}
        if exclude_id:
            query["_id"] = {"$ne": exclude_id}
        return self._col.count_documents(query) > 0
