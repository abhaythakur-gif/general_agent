"""
app/controllers/auth/auth_controller.py
========================================
FastAPI router that handles all **Auth** HTTP endpoints.

Design principles
-----------------
* **Controller** — validates requests, delegates to ``app.services.auth_service``.
* Auth in this platform is *header-based*, not token-based.  Callers pass
  ``X-User-ID: <user_id>`` on every authenticated request.
* The ``/auth/init`` endpoint must be called once before using any other
  authenticated endpoint.

Authentication model
--------------------
```
Client                          API
  │                              │
  │  POST /auth/init             │
  │  { "user_id": "alice" }      │
  │─────────────────────────────▶│  Creates user in MongoDB (idempotent)
  │◀─────────────────────────────│
  │  { "user_id": "alice",       │
  │    "is_new": true }          │
  │                              │
  │  GET /agents                 │
  │  X-User-ID: alice            │
  │─────────────────────────────▶│  Reads user from header on every call
  │◀─────────────────────────────│
```

Prefix
------
All routes are mounted at ``/api/v1/auth`` in ``main.py``.
"""

from fastapi import APIRouter, Depends, status

from app.controllers.auth.schema.request.auth_request import AuthInitRequest
from app.controllers.auth.schema.response.auth_response import AuthInitOut, UserProfileOut
from app.services.auth.service import get_current_user_id, init_user, get_user_profile

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# ---------------------------------------------------------------------------
# POST /auth/init  — initialise a user account
# ---------------------------------------------------------------------------

@router.post(
    "/init",
    summary="Initialise or re-touch a user account",
    description="""
## Initialise user

Creates a new user record in MongoDB on first call.  Safe to call
multiple times with the same ``user_id`` — the operation is idempotent
(``is_new`` will be ``false`` on subsequent calls).

### No auth required
This is the bootstrapping endpoint — no header needed.

### Rules
- ``user_id`` must be a non-empty string.
- Any printable identifier is valid: ``"alice"``, ``"abhay-123"``, ``"user@company.com"``.

### Example request
```json
{ "user_id": "abhay-123" }
```

### Example response — first call
```json
{ "user_id": "abhay-123", "is_new": true }
```

### Example response — subsequent calls
```json
{ "user_id": "abhay-123", "is_new": false }
```
""",
    response_model=AuthInitOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User created or already exists"},
        400: {"description": "user_id is blank or missing"},
    },
)
def auth_init(request: AuthInitRequest) -> AuthInitOut:
    """Initialise or re-touch a user account in MongoDB."""
    return init_user(request.user_id)


# ---------------------------------------------------------------------------
# GET /auth/me  — get current user profile
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    summary="Get current user profile",
    description="""
## Get my profile

Reads the ``X-User-ID`` header and returns the user document from MongoDB.

### Authentication
Requires the ``X-User-ID`` header.

### Example response
```json
{
  "user_id": "abhay-123",
  "created_at": "2026-03-01T09:00:00Z",
  "last_seen_at": "2026-03-19T10:15:33Z"
}
```
""",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User profile document"},
        401: {"description": "X-User-ID header is missing"},
        404: {"description": "User not found — call POST /auth/init first"},
    },
)
def get_me(user_id: str = Depends(get_current_user_id)) -> UserProfileOut:
    """Return the authenticated user's profile from MongoDB."""
    return get_user_profile(user_id)
