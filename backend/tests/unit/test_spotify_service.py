"""Unit tests for SpotifyService.sync_library."""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from src.services.spotify_service import SpotifyService
from src.middleware.error_handler import ExternalServiceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _playlist(pid: str, name: str = "My Playlist") -> dict:
    return {"id": pid, "name": name}


def _track_item(tid: str, name: str = "Song", artist: str = "Artist", dur: int = 200_000) -> dict:
    # /playlists/{id}/items response shape: track data is under "item", not "track"
    return {
        "item": {
            "id": tid,
            "name": name,
            "type": "track",
            "artists": [{"name": artist}],
            "duration_ms": dur,
        }
    }


def _paging(items: list, next_: str | None = None, total: int | None = None) -> dict:
    return {"items": items, "next": next_, "total": total or len(items)}


def _make_db_track(spotify_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), spotify_track_id=spotify_id)


def _make_db_playlist(sp_id: str, db_id=None) -> SimpleNamespace:
    return SimpleNamespace(id=db_id or uuid.uuid4(), spotify_playlist_id=sp_id, name="")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_user_playlists.return_value = _paging([_playlist("pl1")])
    client.get_playlist_tracks.return_value = _paging([_track_item("t1"), _track_item("t2")])
    client.get_audio_features.return_value = [
        {"id": "t1", "energy": 0.8},
        {"id": "t2", "energy": 0.5},
    ]
    return client


@pytest.fixture
def mock_auth():
    auth = AsyncMock()
    auth.get_valid_access_token.return_value = "access_token_xyz"
    return auth


@pytest.fixture
def mock_track_repo():
    repo = MagicMock()
    repo.bulk_upsert.return_value = [_make_db_track("t1"), _make_db_track("t2")]
    return repo


@pytest.fixture
def mock_playlist_repo():
    repo = MagicMock()
    repo.upsert.return_value = _make_db_playlist("pl1")
    repo.get_by_user.return_value = [_make_db_playlist("pl1")]
    return repo


@pytest.fixture
def mock_vector():
    return MagicMock()


@pytest.fixture
def service(mock_client, mock_auth, mock_track_repo, mock_playlist_repo, mock_vector):
    return SpotifyService(
        spotify_client=mock_client,
        auth_service=mock_auth,
        track_repo=mock_track_repo,
        playlist_repo=mock_playlist_repo,
        vector_search=mock_vector,
    )


@pytest.fixture
def db():
    return MagicMock()


# ---------------------------------------------------------------------------
# Basic sync flow
# ---------------------------------------------------------------------------

class TestSyncLibraryBasicFlow:
    @pytest.mark.asyncio
    async def test_returns_counts(self, service, db):
        result = await service.sync_library(uuid.uuid4(), db)
        assert result["playlists_synced"] == 1
        assert result["tracks_synced"] == 2

    @pytest.mark.asyncio
    async def test_gets_valid_access_token(self, service, mock_auth, db):
        uid = uuid.uuid4()
        await service.sync_library(uid, db)
        mock_auth.get_valid_access_token.assert_called_once_with(uid, db)

    @pytest.mark.asyncio
    async def test_calls_bulk_upsert_with_track_data(self, service, mock_track_repo, db):
        uid = uuid.uuid4()
        await service.sync_library(uid, db)
        mock_track_repo.bulk_upsert.assert_called_once()
        call_args = mock_track_repo.bulk_upsert.call_args
        assert call_args.args[1] == uid
        tracks_data = call_args.args[2]
        assert any(t["spotify_track_id"] == "t1" for t in tracks_data)
        assert any(t["spotify_track_id"] == "t2" for t in tracks_data)

    @pytest.mark.asyncio
    async def test_calls_vector_index_tracks(self, service, mock_vector, mock_track_repo, db):
        uid = uuid.uuid4()
        await service.sync_library(uid, db)
        mock_vector.index_tracks.assert_called_once()
        call_args = mock_vector.index_tracks.call_args
        assert call_args.args[0] == uid

    @pytest.mark.asyncio
    async def test_audio_features_attached_to_tracks(self, service, mock_track_repo, db):
        await service.sync_library(uuid.uuid4(), db)
        tracks_data = mock_track_repo.bulk_upsert.call_args.args[2]
        feat_map = {t["spotify_track_id"]: t["audio_features"] for t in tracks_data}
        assert feat_map["t1"] == {"id": "t1", "energy": 0.8}
        assert feat_map["t2"] == {"id": "t2", "energy": 0.5}


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    @pytest.mark.asyncio
    async def test_fetches_all_playlist_pages(self, service, mock_client, db):
        mock_client.get_user_playlists.side_effect = [
            _paging([_playlist("pl1")], next_="has_more"),
            _paging([_playlist("pl2")]),
        ]
        mock_client.get_playlist_tracks.return_value = _paging([])
        mock_client.get_audio_features.return_value = []

        uid = uuid.uuid4()
        result = await service.sync_library(uid, db)
        assert mock_client.get_user_playlists.call_count == 2
        assert result["playlists_synced"] == 2

    @pytest.mark.asyncio
    async def test_fetches_all_track_pages_for_a_playlist(self, service, mock_client, db):
        mock_client.get_user_playlists.return_value = _paging([_playlist("pl1")])
        mock_client.get_playlist_tracks.side_effect = [
            _paging([_track_item("t1")], next_="has_more"),
            _paging([_track_item("t2")]),
        ]
        mock_client.get_audio_features.return_value = []

        await service.sync_library(uuid.uuid4(), db)
        assert mock_client.get_playlist_tracks.call_count == 2

    @pytest.mark.asyncio
    async def test_deduplicates_tracks_appearing_in_multiple_playlists(
        self, service, mock_client, mock_track_repo, db
    ):
        mock_client.get_user_playlists.return_value = _paging(
            [_playlist("pl1"), _playlist("pl2")]
        )
        mock_client.get_playlist_tracks.return_value = _paging([_track_item("t_shared")])
        mock_client.get_audio_features.return_value = []

        await service.sync_library(uuid.uuid4(), db)
        tracks_data = mock_track_repo.bulk_upsert.call_args.args[2]
        ids = [t["spotify_track_id"] for t in tracks_data]
        assert ids.count("t_shared") == 1


# ---------------------------------------------------------------------------
# on_progress callback
# ---------------------------------------------------------------------------

class TestProgressCallback:
    @pytest.mark.asyncio
    async def test_on_progress_called_once_per_playlist(self, service, mock_client, db):
        mock_client.get_user_playlists.return_value = _paging(
            [_playlist("pl1"), _playlist("pl2"), _playlist("pl3")]
        )
        mock_client.get_playlist_tracks.return_value = _paging([])
        mock_client.get_audio_features.return_value = []

        progress_calls = []
        def on_progress(done, total, tracks):
            progress_calls.append((done, total))

        await service.sync_library(uuid.uuid4(), db, on_progress=on_progress)
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_on_progress_increments_playlists_done(self, service, mock_client, db):
        mock_client.get_user_playlists.return_value = _paging(
            [_playlist("p1"), _playlist("p2")]
        )
        mock_client.get_playlist_tracks.return_value = _paging([])
        mock_client.get_audio_features.return_value = []

        dones = []
        def on_progress(done, total, tracks):
            dones.append(done)

        await service.sync_library(uuid.uuid4(), db, on_progress=on_progress)
        assert dones == [1, 2]

    @pytest.mark.asyncio
    async def test_on_progress_accepts_async_callback(self, service, mock_client, db):
        mock_client.get_user_playlists.return_value = _paging([_playlist("pl1")])
        mock_client.get_playlist_tracks.return_value = _paging([])
        mock_client.get_audio_features.return_value = []

        called = []
        async def async_progress(done, total, tracks):
            called.append(done)

        await service.sync_library(uuid.uuid4(), db, on_progress=async_progress)
        assert called == [1]


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------

class TestExponentialBackoff:
    @pytest.mark.asyncio
    async def test_retries_on_external_service_error(self, service, mock_client, db):
        mock_client.get_user_playlists.side_effect = [
            ExternalServiceError("Spotify", "429 Too Many Requests"),
            _paging([]),
        ]
        mock_client.get_audio_features.return_value = []

        with patch("src.services.spotify_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await service.sync_library(uuid.uuid4(), db)
        mock_sleep.assert_called_once()
        assert result["playlists_synced"] == 0

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, service, mock_client, db):
        mock_client.get_user_playlists.side_effect = ExternalServiceError("Spotify", "500")
        with patch("src.services.spotify_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ExternalServiceError):
                await service.sync_library(uuid.uuid4(), db)
