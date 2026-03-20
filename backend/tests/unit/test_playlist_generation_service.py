"""Unit tests for PlaylistGenerationService."""
import json
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.services.playlist_generation_service import (
    PlaylistGenerationService,
    _matches_filters,
    _parse_audio_features,
)


def _make_track(
    spotify_track_id: str = "t1",
    name: str = "Song",
    artist: str = "Artist",
    audio_features: str | None = None,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        spotify_track_id=spotify_track_id,
        name=name,
        artist=artist,
        duration_ms=200_000,
        audio_features=audio_features,
    )


def _search_result(sid: str, distance: float = 0.1) -> dict:
    return {
        "spotify_track_id": sid,
        "name": f"Track {sid}",
        "artist": f"Artist {sid}",
        "duration_ms": 200_000,
        "distance": distance,
    }


@pytest.fixture
def mock_vector():
    return MagicMock()


@pytest.fixture
def mock_track_repo():
    return MagicMock()


@pytest.fixture
def service(mock_vector, mock_track_repo):
    return PlaylistGenerationService(
        vector_search=mock_vector,
        track_repo=mock_track_repo,
    )


class TestRetrieveTracks:
    def test_returns_tracks_from_db(self, service, mock_vector, mock_track_repo):
        db = MagicMock()
        user_id = uuid.uuid4()
        mock_vector.search.return_value = [_search_result("t1"), _search_result("t2")]
        tracks = [_make_track("t1"), _make_track("t2")]
        mock_track_repo.get_by_spotify_ids.return_value = tracks

        result = service.retrieve_tracks(db, user_id, "upbeat dance music")

        mock_vector.search.assert_called_once_with(
            user_id, "upbeat dance music", n_results=None, max_distance=None
        )
        mock_track_repo.get_by_spotify_ids.assert_called_once_with(
            db, user_id, ["t1", "t2"]
        )
        assert result == tracks

    def test_returns_empty_when_no_search_results(self, service, mock_vector, mock_track_repo):
        mock_vector.search.return_value = []
        result = service.retrieve_tracks(MagicMock(), uuid.uuid4(), "test")
        assert result == []
        mock_track_repo.get_by_spotify_ids.assert_not_called()

    def test_passes_n_results_and_max_distance(self, service, mock_vector, mock_track_repo):
        mock_vector.search.return_value = []
        service.retrieve_tracks(
            MagicMock(), uuid.uuid4(), "test", n_results=50, max_distance=0.5
        )
        _, kwargs = mock_vector.search.call_args
        assert kwargs["n_results"] == 50
        assert kwargs["max_distance"] == 0.5

    def test_audio_filters_applied(self, service, mock_vector, mock_track_repo):
        db = MagicMock()
        user_id = uuid.uuid4()
        mock_vector.search.return_value = [_search_result("t1"), _search_result("t2")]

        track_high_energy = _make_track(
            "t1", audio_features=json.dumps({"energy": 0.9, "tempo": 120})
        )
        track_low_energy = _make_track(
            "t2", audio_features=json.dumps({"energy": 0.2, "tempo": 80})
        )
        mock_track_repo.get_by_spotify_ids.return_value = [track_high_energy, track_low_energy]

        result = service.retrieve_tracks(
            db, user_id, "test", audio_filters={"energy": {"min": 0.5}}
        )
        assert len(result) == 1
        assert result[0].spotify_track_id == "t1"

    def test_audio_filters_skip_tracks_without_features(self, service, mock_vector, mock_track_repo):
        mock_vector.search.return_value = [_search_result("t1")]
        track = _make_track("t1", audio_features=None)
        mock_track_repo.get_by_spotify_ids.return_value = [track]

        result = service.retrieve_tracks(
            MagicMock(), uuid.uuid4(), "test", audio_filters={"energy": {"min": 0.5}}
        )
        assert result == []


class TestParseAudioFeatures:
    def test_parses_json_string(self):
        assert _parse_audio_features('{"energy": 0.8}') == {"energy": 0.8}

    def test_returns_none_for_none(self):
        assert _parse_audio_features(None) is None

    def test_returns_dict_as_is(self):
        d = {"energy": 0.8}
        assert _parse_audio_features(d) is d

    def test_returns_none_for_invalid_json(self):
        assert _parse_audio_features("not json") is None


class TestMatchesFilters:
    def test_passes_when_in_range(self):
        assert _matches_filters({"energy": 0.7, "tempo": 120}, {"energy": {"min": 0.5, "max": 0.9}})

    def test_fails_below_min(self):
        assert not _matches_filters({"energy": 0.3}, {"energy": {"min": 0.5}})

    def test_fails_above_max(self):
        assert not _matches_filters({"energy": 0.9}, {"energy": {"max": 0.8}})

    def test_fails_when_feature_missing(self):
        assert not _matches_filters({}, {"energy": {"min": 0.5}})

    def test_empty_filters_always_pass(self):
        assert _matches_filters({"energy": 0.5}, {})
