"""
app/controllers/auth/schema/request/auth_request.py
=====================================================
Pydantic request schemas for the Auth controller.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthInitRequest(BaseModel):
    """
    Request body for **POST /auth/init**.

    Creates (or re-touches) a user account in MongoDB.  Safe to call
    multiple times with the same ``user_id`` — it is idempotent.

    ### Rules
    - ``user_id`` must be a non-empty string.
    - Any printable ASCII identifier is valid (e.g. ``"alice"``,
      ``"abhay-123"``, ``"user@company.com"``).

    ### Example
    ```json
    { "user_id": "abhay-123" }
    ```
    """

    user_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the user (choose any non-empty string)",
    )
