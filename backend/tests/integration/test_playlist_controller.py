"""Integration tests for POST /playlist/generate and save-to-spotify."""
import uuid

import pytest
from cryptography.fernet import Fernet

from src.middleware.auth_middleware import create_access_token
from src.repositories.playlist_repository import PlaylistRepository
from src.repositories.track_repository import TrackRepository
from src.repositories.user_repository import UserRepository
from src.services.llm_service import LLMService, PlaylistLLMOutput
from src.services.playlist_generation_service import PlaylistGenerationService
from src.services.spotify_service import SpotifyService


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
    user = UserRepository().upsert(db, spotify_id="playlist_ctrl_user")
    db.commit()
    token = create_access_token(user.id)
    return user, token


def test_post_generate_unauthenticated(client):
    response = client.post("/playlist/generate", json={"text": "some playlist please"})
    assert response.status_code == 401


def test_post_generate_returns_playlist(client, authed_user, db, monkeypatch):
    user, token = authed_user
    tid = "tid00000000000000000001"
    tr = TrackRepository()
    tr.bulk_upsert(
        db,
        user.id,
        [
            {
                "spotify_track_id": tid,
                "name": "Song",
                "artist": "Artist",
                "duration_ms": 45 * 60 * 1000,
                "audio_features": None,
            }
        ],
    )
    db.flush()
    track_row = tr.get_by_spotify_ids(db, user.id, [tid])[0]

    def fake_retrieve(self, db_sess, uid, q):
        assert uid == user.id
        return [track_row]

    monkeypatch.setattr(PlaylistGenerationService, "retrieve_tracks", fake_retrieve)

    def fake_llm(self, messages):
        return PlaylistLLMOutput(name="Integration PL", track_ids=[tid])

    monkeypatch.setattr(LLMService, "generate_playlist_output", fake_llm)

    response = client.post(
        "/playlist/generate",
        json={"text": "About 45 minutes of music"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Integration PL"
    assert data["track_count"] == 1
    assert data["playlist_tracks"][0]["track"]["spotify_track_id"] == tid


def test_post_save_to_spotify_unauthenticated(client):
    response = client.post(f"/playlist/{uuid.uuid4()}/save-to-spotify")
    assert response.status_code == 401


def test_post_save_to_spotify_not_found(client, authed_user):
    user, token = authed_user
    missing = uuid.uuid4()
    response = client.post(
        f"/playlist/{missing}/save-to-spotify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_post_save_to_spotify_conflict_when_already_linked(client, authed_user, db, monkeypatch):
    user, token = authed_user
    tid = "tid00000000000000000001"
    tr = TrackRepository()
    tr.bulk_upsert(
        db,
        user.id,
        [
            {
                "spotify_track_id": tid,
                "name": "Song",
                "artist": "Artist",
                "duration_ms": 60_000,
                "audio_features": None,
            }
        ],
    )
    db.flush()
    track_row = tr.get_by_spotify_ids(db, user.id, [tid])[0]
    pr = PlaylistRepository()
    pl = pr.create_ai_playlist(db, user.id, "Saved PL")
    pr.add_tracks(db, pl.id, [(track_row.id, 1)])
    pr.link_spotify_playlist(db, pl.id, user.id, "sp_pl_" + "x" * 16)
    db.commit()

    response = client.post(
        f"/playlist/{pl.id}/save-to-spotify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


def test_post_save_to_spotify_success(client, authed_user, db, monkeypatch):
    user, token = authed_user
    tid = "tid00000000000000000002"
    tr = TrackRepository()
    tr.bulk_upsert(
        db,
        user.id,
        [
            {
                "spotify_track_id": tid,
                "name": "Song",
                "artist": "Artist",
                "duration_ms": 60_000,
                "audio_features": None,
            }
        ],
    )
    db.flush()
    track_row = tr.get_by_spotify_ids(db, user.id, [tid])[0]
    pr = PlaylistRepository()
    pl = pr.create_ai_playlist(db, user.id, "To Save")
    pr.add_tracks(db, pl.id, [(track_row.id, 1)])
    db.commit()

    sp_id = "sp_pl_" + "s" * 16

    async def fake_save(self, db_sess, u, p):
        r = PlaylistRepository()
        r.link_spotify_playlist(db_sess, p.id, u.id, sp_id)
        return r.get_with_tracks(db_sess, p.id)

    monkeypatch.setattr(SpotifyService, "save_playlist_to_spotify", fake_save)

    response = client.post(
        f"/playlist/{pl.id}/save-to-spotify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spotify_playlist_id"] == sp_id
    assert "open.spotify.com" in (data.get("spotify_playlist_url") or "")
