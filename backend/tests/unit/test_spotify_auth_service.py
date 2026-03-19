from datetime import datetime, timedelta, timezone
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


@pytest.fixture
def mock_spotify_client():
    client = MagicMock()
    client.build_auth_url.return_value = "https://accounts.spotify.com/authorize?code_challenge=abc"
    client.exchange_code = AsyncMock(return_value={
        "access_token": "access_abc",
        "refresh_token": "refresh_xyz",
        "expires_in": 3600,
    })
    client.get_current_user = AsyncMock(return_value={"id": "spotify_user_123"})
    client.refresh_access_token = AsyncMock(return_value={
        "access_token": "new_access_token",
        "expires_in": 3600,
    })
    return client


@pytest.fixture
def service(mock_spotify_client):
    from src.repositories.user_repository import UserRepository
    from src.repositories.token_repository import TokenRepository
    from src.utils.token_encryptor import TokenEncryptor
    from src.services.spotify_auth_service import SpotifyAuthService

    return SpotifyAuthService(
        spotify_client=mock_spotify_client,
        user_repo=UserRepository(),
        token_repo=TokenRepository(),
        encryptor=TokenEncryptor(),
    )


def test_generate_auth_url_returns_url_and_state(service):
    url, state = service.generate_auth_url()
    assert url.startswith("https://accounts.spotify.com/authorize")
    assert len(state) > 20


def test_generate_auth_url_unique_states(service):
    _, state1 = service.generate_auth_url()
    _, state2 = service.generate_auth_url()
    assert state1 != state2


@pytest.mark.asyncio
async def test_handle_callback_creates_user_and_token(service, db):
    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)
    assert user.spotify_id == "spotify_user_123"
    assert user.id is not None


@pytest.mark.asyncio
async def test_handle_callback_invalid_state_raises(service, db):
    with pytest.raises(AuthenticationError):
        await service.handle_callback(code="auth_code", state="bad_state", db=db)


@pytest.mark.asyncio
async def test_handle_callback_state_can_only_be_used_once(service, db):
    _, state = service.generate_auth_url()
    await service.handle_callback(code="auth_code", state=state, db=db)
    # Using same state a second time should fail
    with pytest.raises(AuthenticationError):
        await service.handle_callback(code="auth_code", state=state, db=db)


@pytest.mark.asyncio
async def test_get_valid_access_token_non_expired(service, db):
    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)

    token = await service.get_valid_access_token(user.id, db)
    assert token == "access_abc"
    # Spotify client should NOT have been called for a refresh
    service._client.refresh_access_token.assert_not_called()


@pytest.mark.asyncio
async def test_get_valid_access_token_expired_refreshes(service, db):
    from src.repositories.token_repository import TokenRepository
    from src.utils.token_encryptor import TokenEncryptor

    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)

    # Force the token to appear expired in the DB
    encryptor = TokenEncryptor()
    token_repo = TokenRepository()
    token_repo.upsert(
        db,
        user_id=user.id,
        encrypted_access_token=encryptor.encrypt("old_access"),
        encrypted_refresh_token=encryptor.encrypt("refresh_xyz"),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.commit()

    new_token = await service.get_valid_access_token(user.id, db)
    assert new_token == "new_access_token"
    service._client.refresh_access_token.assert_called_once_with("refresh_xyz")
