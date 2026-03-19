from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import create_access_token, get_current_user
from src.middleware.error_handler import AuthenticationError
from src.models.database import get_db
from src.models.user import User
from src.schemas.user_schema import UserResponse
from src.services.spotify_auth_service import SpotifyAuthService, get_spotify_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login(
    auth_service: SpotifyAuthService = Depends(get_spotify_auth_service),
) -> dict[str, str]:
    """Generate a Spotify authorization URL and return it to the frontend.

    The frontend is responsible for redirecting the user to this URL.
    The state parameter is embedded in the URL; the frontend must pass it
    back verbatim when calling /auth/callback.
    """
    url, _state = auth_service.generate_auth_url()
    return {"url": url}


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    auth_service: SpotifyAuthService = Depends(get_spotify_auth_service),
) -> dict[str, str]:
    """Handle the Spotify OAuth callback.

    Spotify redirects the user to the frontend /callback page with ?code=&state=.
    The frontend forwards these query params to this endpoint.

    Returns a signed JWT that the frontend stores and uses for subsequent requests.
    """
    if not code or not state:
        raise AuthenticationError("Missing code or state parameter")

    user = await auth_service.handle_callback(code=code, state=state, db=db)
    access_token = create_access_token(user.id)
    return {"access_token": access_token}


@router.post("/logout")
def logout() -> dict[str, str]:
    """Signal logout. The frontend is responsible for clearing the stored JWT.

    This endpoint exists so future server-side session invalidation (e.g. token
    blocklist) can be added without changing the frontend contract.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
