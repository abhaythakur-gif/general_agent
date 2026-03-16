from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.response import UserInitResponse, UserProfileResponse
from app.services.auth_service import get_current_user_id, init_user, get_user_profile

router = APIRouter(prefix="/auth", tags=["Auth"])


class InitRequest(BaseModel):
    user_id: str


@router.post("/init", summary="Initialise or re-touch a user account", response_model=UserInitResponse,
             responses={200: {"description": "User created or already exists"}, 400: {"description": "user_id is blank"}})
def auth_init(request: InitRequest):
    """
    Creates the user in MongoDB on first call. Safe to call repeatedly.

    **Request:** `{ "user_id": "abhay-123" }`
    **Response:** `{ "user_id": "abhay-123", "is_new": true }`
    """
    return init_user(request.user_id)


@router.get("/me", summary="Get current user profile", response_model=UserProfileResponse,
            responses={200: {"description": "User profile"}, 404: {"description": "User not found"}})
def me(user_id: str = Depends(get_current_user_id)):
    """
    Reads **X-User-ID** header and returns the user document from MongoDB.
    """
    return get_user_profile(user_id)
