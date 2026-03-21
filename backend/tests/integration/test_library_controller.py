"""Integration tests for LibraryController."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.middleware.auth_middleware import create_access_token
from src.models.user import User
from src.repositories.user_repository import UserRepository


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    from src.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def authed_user(db):
    """Create a real user in the test DB and return (user, jwt_token)."""
    repo = UserRepository()
    user = repo.upsert(db, spotify_id="library_test_user")
    db.commit()
    token = create_access_token(user.id)
    return user, token


# ---------------------------------------------------------------------------
# POST /library/sync
# ---------------------------------------------------------------------------

class TestPostSync:
    def test_unauthenticated_returns_401(self, client):
        response = client.post("/library/sync")
        assert response.status_code == 401

    def test_authenticated_returns_started(self, client, authed_user):
        _, token = authed_user
        with patch(
            "src.controllers.library_controller.SpotifyService"
        ) as mock_service_cls:
            mock_instance = mock_service_cls.return_value
            mock_instance.sync_library = AsyncMock(
                return_value={"playlists_synced": 5, "tracks_synced": 100}
            )
            response = client.post(
                "/library/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "started"

    def test_invalid_token_returns_401(self, client):
        response = client.post(
            "/library/sync",
            headers={"Authorization": "Bearer not_a_real_token"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /library/status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/library/status")
        assert response.status_code == 401

    def test_authenticated_returns_status_field(self, client, authed_user):
        _, token = authed_user
        response = client.get(
            "/library/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "status" in body

    def test_initial_status_is_idle(self, client, authed_user):
        user, token = authed_user
        # Clear any state left from other tests
        from src.controllers.library_controller import _sync_state
        _sync_state.pop(str(user.id), None)

        response = client.get(
            "/library/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["status"] == "idle"

    def test_status_reflects_set_state(self, client, authed_user):
        user, token = authed_user
        from src.controllers.library_controller import _set_state
        _set_state(user.id, status="syncing", playlists_done=3, total_playlists=10, tracks_done=300)

        response = client.get(
            "/library/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = response.json()
        assert body["status"] == "syncing"
        assert body["playlists_done"] == 3
        assert body["tracks_done"] == 300


# ---------------------------------------------------------------------------
# WebSocket /library/sync/ws
# ---------------------------------------------------------------------------

class TestSyncWebSocket:
    def test_invalid_token_closes_connection(self, client):
        from starlette.websockets import WebSocketDisconnect
        # Starlette TestClient raises WebSocketDisconnect at __enter__ when the
        # server closes before the client sends the first message (code 4001).
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/library/sync/ws?token=bad_token"):
                pass
        assert exc_info.value.code == 4001

    def test_valid_token_receives_status_messages(self, client, authed_user):
        user, token = authed_user
        from src.controllers.library_controller import _set_state, _sync_state
        _set_state(user.id, status="complete", playlists_done=5, total_playlists=5, tracks_done=100)

        with client.websocket_connect(f"/library/sync/ws?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["status"] == "complete"
            assert msg["playlists_done"] == 5
            assert msg["tracks_done"] == 100
