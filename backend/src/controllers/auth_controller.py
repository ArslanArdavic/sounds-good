from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import get_current_user
from src.models.database import get_db
from src.models.user import User
from src.schemas.user_schema import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login() -> dict[str, str]:
    """
    Returns the Spotify OAuth authorization URL.
    The frontend redirects the user to this URL to begin the OAuth flow.
    Phase 1: will delegate to SpotifyAuthService.authorize_url().
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Spotify OAuth not yet implemented — coming in Phase 1",
    )


@router.get("/callback")
def callback(code: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Handles the Spotify OAuth callback.
    Exchanges the authorization code for tokens, creates/retrieves the user,
    and returns a signed JWT for subsequent API calls.
    Phase 1: will delegate to SpotifyAuthService.get_access_token() and UserRepository.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Spotify OAuth callback not yet implemented — coming in Phase 1",
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Returns the authenticated user's profile."""
    return current_user
