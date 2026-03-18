"""
app/services/auth/service.py
------------------------------
Auth business logic — user_id header based identity.
Replaces app/services/auth_service.py.
"""

from fastapi import Header, HTTPException
from resources.mongodb import get_mongo_db, get_or_create_user


def get_current_user_id(x_user_id: str = Header(..., description="Your unique user ID")) -> str:
    uid = x_user_id.strip()
    if not uid:
        raise HTTPException(status_code=400, detail="X-User-ID header must not be empty")
    get_or_create_user(uid)
    return uid


def init_user(user_id: str) -> dict:
    uid = user_id.strip()
    if not uid:
        raise HTTPException(status_code=400, detail="user_id must not be empty")
    return get_or_create_user(uid)


def get_user_profile(user_id: str) -> dict:
    db = get_mongo_db()
    doc = db["users"].find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    doc.pop("_id", None)
    doc["user_id"] = user_id
    return doc
