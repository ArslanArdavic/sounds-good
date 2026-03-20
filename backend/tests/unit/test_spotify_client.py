"""Unit tests for the new SpotifyClient data-fetching methods (Phase 2)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.error_handler import ExternalServiceError


@pytest.fixture
def client():
    """Return a SpotifyClient with settings env vars set."""
    with patch("src.clients.spotify_client.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            spotify_client_id="client_id",
            spotify_client_secret="client_secret",
            spotify_redirect_uri="http://localhost:3000/callback",
        )
        from src.clients.spotify_client import SpotifyClient
        return SpotifyClient()


def _mock_response(status_code: int, json_body: dict):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_body
    mock.text = str(json_body)
    return mock


# ---------------------------------------------------------------------------
# get_user_playlists
# ---------------------------------------------------------------------------

class TestGetUserPlaylists:
    @pytest.mark.asyncio
    async def test_returns_paging_object(self, client):
        expected = {"items": [{"id": "pl1"}], "total": 1, "next": None, "offset": 0, "limit": 50}
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(200, expected)
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get_user_playlists("token123")
        assert result == expected

    @pytest.mark.asyncio
    async def test_sends_correct_url_and_params(self, client):
        mock_get = AsyncMock(
            return_value=_mock_response(200, {"items": [], "total": 0})
        )
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = mock_get
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            await client.get_user_playlists("tok", offset=50, limit=20)
        call_kwargs = mock_get.call_args
        assert "me/playlists" in call_kwargs.args[0]
        assert call_kwargs.kwargs["params"]["offset"] == 50
        assert call_kwargs.kwargs["params"]["limit"] == 20

    @pytest.mark.asyncio
    async def test_raises_on_non_200(self, client):
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(401, {"error": "Unauthorized"})
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(ExternalServiceError):
                await client.get_user_playlists("bad_token")


# ---------------------------------------------------------------------------
# get_playlist_tracks
# ---------------------------------------------------------------------------

class TestGetPlaylistTracks:
    @pytest.mark.asyncio
    async def test_returns_paging_object(self, client):
        expected = {"items": [{"track": {"id": "t1", "name": "Song"}}], "total": 1}
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(200, expected)
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get_playlist_tracks("token", "playlist123")
        assert result == expected

    @pytest.mark.asyncio
    async def test_sends_correct_url_and_pagination(self, client):
        mock_get = AsyncMock(
            return_value=_mock_response(200, {"items": [], "total": 0})
        )
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = mock_get
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            await client.get_playlist_tracks("tok", "pl99", offset=100, limit=50)
        call_kwargs = mock_get.call_args
        assert "pl99/tracks" in call_kwargs.args[0]
        assert call_kwargs.kwargs["params"]["offset"] == 100
        assert call_kwargs.kwargs["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_raises_on_non_200(self, client):
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(403, {"error": "Forbidden"})
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(ExternalServiceError):
                await client.get_playlist_tracks("tok", "pl1")


# ---------------------------------------------------------------------------
# get_audio_features
# ---------------------------------------------------------------------------

class TestGetAudioFeatures:
    @pytest.mark.asyncio
    async def test_returns_features_list(self, client):
        features = [{"id": "t1", "energy": 0.8}, {"id": "t2", "energy": 0.5}]
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(200, {"audio_features": features})
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get_audio_features("tok", ["t1", "t2"])
        assert result == features

    @pytest.mark.asyncio
    async def test_filters_out_none_features(self, client):
        features = [{"id": "t1", "energy": 0.8}, None, {"id": "t3", "energy": 0.3}]
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(200, {"audio_features": features})
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get_audio_features("tok", ["t1", "t2", "t3"])
        assert len(result) == 2
        assert all(f is not None for f in result)

    @pytest.mark.asyncio
    async def test_batches_more_than_100_tracks(self, client):
        """A list of 150 IDs must produce exactly 2 HTTP requests."""
        track_ids = [f"t{i}" for i in range(150)]
        single_batch_response = _mock_response(
            200, {"audio_features": [{"id": f"t{i}"} for i in range(100)]}
        )
        second_batch_response = _mock_response(
            200, {"audio_features": [{"id": f"t{i}"} for i in range(100, 150)]}
        )
        mock_get = AsyncMock(
            side_effect=[single_batch_response, second_batch_response]
        )
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = mock_get
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get_audio_features("tok", track_ids)
        assert mock_get.call_count == 2
        assert len(result) == 150

    @pytest.mark.asyncio
    async def test_first_batch_ids_sent_correctly(self, client):
        track_ids = ["a", "b", "c"]
        mock_get = AsyncMock(
            return_value=_mock_response(
                200, {"audio_features": [{"id": x} for x in track_ids]}
            )
        )
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = mock_get
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            await client.get_audio_features("tok", track_ids)
        sent_ids = mock_get.call_args.kwargs["params"]["ids"]
        assert sent_ids == "a,b,c"

    @pytest.mark.asyncio
    async def test_raises_on_non_200(self, client):
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(500, {"error": "Server Error"})
        )
        with patch("src.clients.spotify_client.httpx.AsyncClient", return_value=mock_http):
            with pytest.raises(ExternalServiceError):
                await client.get_audio_features("tok", ["t1"])

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, client):
        """No HTTP call should be made for an empty input list."""
        with patch("src.clients.spotify_client.httpx.AsyncClient") as mock_cls:
            result = await client.get_audio_features("tok", [])
        mock_cls.assert_not_called()
        assert result == []
