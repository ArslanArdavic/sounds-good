"""Unit tests for TrackRepository."""
import uuid

import pytest

from src.models.track import Track
from src.models.user import User
from src.repositories.track_repository import TrackRepository


@pytest.fixture
def repo():
    return TrackRepository()


@pytest.fixture
def user(db):
    u = User(spotify_id="test_user_spotify_id")
    db.add(u)
    db.flush()
    return u


def _insert_tracks(db, user_id: uuid.UUID, spotify_ids: list[str]) -> list[Track]:
    tracks = []
    for sid in spotify_ids:
        t = Track(
            user_id=user_id,
            spotify_track_id=sid,
            name=f"Track {sid}",
            artist=f"Artist {sid}",
            duration_ms=200_000,
        )
        tracks.append(t)
    db.add_all(tracks)
    db.flush()
    return tracks


class TestGetBySpotifyIds:
    def test_returns_tracks_in_requested_order(self, db, user, repo):
        _insert_tracks(db, user.id, ["t3", "t1", "t2"])
        result = repo.get_by_spotify_ids(db, user.id, ["t2", "t3", "t1"])
        assert [t.spotify_track_id for t in result] == ["t2", "t3", "t1"]

    def test_skips_missing_ids(self, db, user, repo):
        _insert_tracks(db, user.id, ["t1", "t2"])
        result = repo.get_by_spotify_ids(db, user.id, ["t1", "missing", "t2"])
        assert [t.spotify_track_id for t in result] == ["t1", "t2"]

    def test_returns_empty_for_empty_input(self, db, user, repo):
        result = repo.get_by_spotify_ids(db, user.id, [])
        assert result == []

    def test_returns_empty_when_no_tracks_exist(self, db, user, repo):
        result = repo.get_by_spotify_ids(db, user.id, ["t1"])
        assert result == []

    def test_scoped_to_user(self, db, repo):
        user_a = User(spotify_id="user_a")
        user_b = User(spotify_id="user_b")
        db.add_all([user_a, user_b])
        db.flush()

        _insert_tracks(db, user_a.id, ["t1"])
        _insert_tracks(db, user_b.id, ["t1"])

        result = repo.get_by_spotify_ids(db, user_a.id, ["t1"])
        assert len(result) == 1
        assert result[0].user_id == user_a.id
