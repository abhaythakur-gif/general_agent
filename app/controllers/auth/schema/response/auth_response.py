"""
app/controllers/auth/schema/response/auth_response.py
======================================================
Pydantic response schemas for the Auth controller.
"""

from __future__ import annotations

from pydantic import BaseModel


class AuthInitOut(BaseModel):
    """
    Returned by **POST /auth/init**.

    | Field    | Description                                           |
    |----------|-------------------------------------------------------|
    | ``user_id`` | The identifier that was initialised                |
    | ``is_new``  | ``true`` on first call; ``false`` on subsequent ones |
    """

    user_id: str
    is_new: bool


class UserProfileOut(BaseModel):
    """
    Returned by **GET /auth/me**.

    | Field           | Description                                |
    |-----------------|--------------------------------------------|
    | ``user_id``     | The caller's identifier                    |
    | ``created_at``  | ISO-8601 timestamp of first ``/auth/init`` |
    | ``last_seen_at``| ISO-8601 timestamp of most recent request  |
    """

    user_id: str
    created_at: str
    last_seen_at: str
