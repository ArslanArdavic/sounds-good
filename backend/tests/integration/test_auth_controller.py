import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

from src.middleware.error_handler import AuthenticationError


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    from src.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_login_returns_spotify_url(client):
    """GET /auth/login should return a Spotify authorization URL."""
    mock_service = MagicMock()
    mock_service.generate_auth_url.return_value = (
        "https://accounts.spotify.com/authorize?client_id=x&state=abc",
        "abc",
    )

    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/login")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "accounts.spotify.com" in data["url"]


def test_callback_missing_code_returns_4xx(client):
    """GET /auth/callback without code param should return 401 or 422."""
    response = client.get("/auth/callback?state=some_state")
    assert response.status_code in (401, 422)


def test_callback_missing_state_returns_4xx(client):
    """GET /auth/callback without state param should return 401 or 422."""
    response = client.get("/auth/callback?code=some_code")
    assert response.status_code in (401, 422)


def test_callback_invalid_state_returns_401(client):
    """GET /auth/callback with unknown state should return 401."""
    mock_service = MagicMock()
    mock_service.handle_callback = AsyncMock(
        side_effect=AuthenticationError("Invalid or expired OAuth state parameter")
    )

    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/callback?code=some_code&state=bad_state")
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_callback_success_returns_access_token(client):
    """GET /auth/callback with valid code+state should return a JWT."""
    from src.models.user import User
    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()

    mock_service = MagicMock()
    mock_service.handle_callback = AsyncMock(
        return_value=(fake_user, ["user-read-email", "user-read-private"])
    )

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/callback?code=real_code&state=real_state")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 20  # JWT is a non-trivial string

    from jose import jwt as jose_jwt

    from src.config import get_settings

    payload = jose_jwt.decode(
        data["access_token"],
        get_settings().secret_key,
        algorithms=["HS256"],
    )
    assert payload["scopes"] == ["user-read-email", "user-read-private"]


def test_me_unauthenticated_returns_401(client):
    """GET /auth/me without a Bearer token should return 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_authenticated_returns_user(client, db):
    """GET /auth/me with a valid JWT should return the user profile."""
    from src.middleware.auth_middleware import create_access_token
    from src.repositories.user_repository import UserRepository

    user_repo = UserRepository()
    user = user_repo.upsert(db, spotify_id="test_spotify_id_999")
    db.commit()

    token = create_access_token(user.id)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["spotify_id"] == "test_spotify_id_999"


def test_logout_returns_200(client):
    """POST /auth/logout should always return 200."""
    response = client.post("/auth/logout")
    assert response.status_code == 200
