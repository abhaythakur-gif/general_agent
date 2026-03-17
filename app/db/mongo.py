"""
app/db/mongo.py
---------------
MongoDB client factory — single shared connection pool.
"""

from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from app.core.config import settings

_client: MongoClient | None = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
    return _client


def get_mongo_db() -> Database:
    """Return the configured MongoDB database handle."""
    return _get_client()[settings.MONGODB_DB_NAME]


def ensure_indexes() -> None:
    """Create all required indexes. Safe to call on every startup."""
    db = get_mongo_db()
    db["agents"].create_index([("user_id", ASCENDING)], name="agents_user_id")
    db["workflows"].create_index([("user_id", ASCENDING)], name="workflows_user_id")
    db["execution_logs"].create_index([("user_id", ASCENDING)], name="exec_user_id")
    db["execution_logs"].create_index([("workflow_id", ASCENDING)], name="exec_workflow_id")
    db["execution_logs"].create_index([("status", ASCENDING)], name="exec_status")
    db["tools"].create_index([("category", ASCENDING)], name="tools_category")

    # ── Chat memory indexes ──────────────────────────────────────────────────
    db["chat_sessions"].create_index(
        [("user_id", ASCENDING), ("tenant_id", ASCENDING)],
        name="chat_sessions_user_tenant",
    )
    db["chat_sessions"].create_index(
        [("user_id", ASCENDING), ("last_message_at", ASCENDING)],
        name="chat_sessions_user_last_msg",
    )
    db["chat_messages"].create_index(
        [("session_id", ASCENDING), ("timestamp", ASCENDING)],
        name="chat_messages_session_ts",
    )
    db["chat_messages"].create_index(
        [("user_id", ASCENDING)],
        name="chat_messages_user_id",
    )


def get_or_create_user(user_id: str) -> dict:
    """
    Look up a user by ID.
    - If found   → update last_seen_at and return {"user_id": ..., "is_new": False}.
    - If not found → insert a new document and return {"user_id": ..., "is_new": True}.
    """
    db = get_mongo_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = db["users"].find_one({"_id": user_id})
    if existing:
        db["users"].update_one({"_id": user_id}, {"$set": {"last_seen_at": now}})
        return {"user_id": user_id, "is_new": False}

    db["users"].insert_one({"_id": user_id, "created_at": now, "last_seen_at": now})
    return {"user_id": user_id, "is_new": True}
