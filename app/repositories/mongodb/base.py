"""
app/repositories/mongodb/base.py
---------------------------------
Abstract base class that every MongoDB repository extends.
Defines the standard CRUD interface so services depend on the
abstraction, not the concrete implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_mongo(doc: Optional[dict]) -> Optional[dict]:
    """Remove the internal '_id' key from a MongoDB document."""
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d


class BaseMongoRepository(ABC):
    """
    Minimal abstract CRUD interface for a single MongoDB collection.
    Concrete subclasses bind to a specific collection via __init__.
    """

    @abstractmethod
    def save(self, data: dict, *args: Any, **kwargs: Any) -> dict:
        """Persist a new document and return it (without _id)."""

    @abstractmethod
    def list_by_user(self, user_id: str) -> list:
        """Return all documents owned by user_id."""

    @abstractmethod
    def get(self, doc_id: str, *args: Any, **kwargs: Any) -> Optional[dict]:
        """Look up a single document by its primary key."""

    @abstractmethod
    def update(self, doc_id: str, *args: Any, **kwargs: Any) -> Optional[dict]:
        """Apply a partial update and return the updated document."""

    @abstractmethod
    def delete(self, doc_id: str, *args: Any, **kwargs: Any) -> bool:
        """Remove a document. Returns True if deleted."""
