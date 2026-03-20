"""Unit tests for TrackRepository."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.models.user import User
from src.repositories.track_repository import TrackRepository


@pytest.fixture
def user(db):
    u = User(spotify_id="test_user_001")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def repo():
    return TrackRepository()


def _track_data(n: int = 1) -> list[dict]:
    return [
        {
            "spotify_track_id": f"track_{i:04d}",
            "name": f"Track {i}",
            "artist": f"Artist {i}",
            "duration_ms": 200_000 + i,
            "audio_features": {"energy": 0.5 + i * 0.01},
        }
        for i in range(n)
    ]


class TestBulkUpsert:
    def test_inserts_new_tracks(self, db, user, repo):
        data = _track_data(3)
        result = repo.bulk_upsert(db, user.id, data)
        assert len(result) == 3
        assert {t.spotify_track_id for t in result} == {"track_0000", "track_0001", "track_0002"}

    def test_updates_existing_track(self, db, user, repo):
        repo.bulk_upsert(db, user.id, _track_data(1))
        updated = [{"spotify_track_id": "track_0000", "name": "New Name", "artist": "New Artist", "duration_ms": 999, "audio_features": None}]
        result = repo.bulk_upsert(db, user.id, updated)
        assert len(result) == 1
        assert result[0].name == "New Name"
        assert result[0].artist == "New Artist"

    def test_no_duplicate_on_re_upsert(self, db, user, repo):
        data = _track_data(2)
        repo.bulk_upsert(db, user.id, data)
        repo.bulk_upsert(db, user.id, data)
        all_tracks = repo.get_by_user(db, user.id)
        assert len(all_tracks) == 2

    def test_audio_features_serialised_as_json(self, db, user, repo):
        data = [{"spotify_track_id": "t1", "name": "A", "artist": "B", "duration_ms": 100, "audio_features": {"energy": 0.8}}]
        result = repo.bulk_upsert(db, user.id, data)
        import json
        assert json.loads(result[0].audio_features) == {"energy": 0.8}

    def test_none_audio_features_stored_as_null(self, db, user, repo):
        data = [{"spotify_track_id": "t1", "name": "A", "artist": "B", "duration_ms": 100, "audio_features": None}]
        result = repo.bulk_upsert(db, user.id, data)
        assert result[0].audio_features is None

    def test_cached_at_is_set_on_insert(self, db, user, repo):
        before = datetime.now(timezone.utc)
        result = repo.bulk_upsert(db, user.id, _track_data(1))
        after = datetime.now(timezone.utc)
        cached_at = result[0].cached_at.replace(tzinfo=timezone.utc) if result[0].cached_at.tzinfo is None else result[0].cached_at
        assert before <= cached_at <= after

    def test_returns_empty_list_for_empty_input(self, db, user, repo):
        result = repo.bulk_upsert(db, user.id, [])
        assert result == []


class TestDeleteStale:
    def test_removes_tracks_older_than_24h(self, db, user, repo):
        from src.models.track import Track
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        old_track = Track(
            user_id=user.id,
            spotify_track_id="old_track",
            name="Old",
            artist="Old Artist",
            duration_ms=100,
            cached_at=old_time,
        )
        db.add(old_track)
        db.flush()

        deleted = repo.delete_stale(db, user.id)
        assert deleted == 1
        remaining = repo.get_by_user(db, user.id)
        assert not any(t.spotify_track_id == "old_track" for t in remaining)

    def test_keeps_fresh_tracks(self, db, user, repo):
        repo.bulk_upsert(db, user.id, _track_data(2))
        deleted = repo.delete_stale(db, user.id)
        assert deleted == 0
        assert len(repo.get_by_user(db, user.id)) == 2

    def test_does_not_delete_other_users_tracks(self, db, repo):
        user_a = User(spotify_id="user_a")
        user_b = User(spotify_id="user_b")
        db.add_all([user_a, user_b])
        db.flush()

        from src.models.track import Track
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        track_b = Track(
            user_id=user_b.id,
            spotify_track_id="b_track",
            name="B",
            artist="B Artist",
            duration_ms=100,
            cached_at=old_time,
        )
        db.add(track_b)
        db.flush()

        repo.delete_stale(db, user_a.id)
        assert len(repo.get_by_user(db, user_b.id)) == 1


class TestGetByUser:
    def test_returns_only_this_users_tracks(self, db, repo):
        user_a = User(spotify_id="user_x")
        user_b = User(spotify_id="user_y")
        db.add_all([user_a, user_b])
        db.flush()

        repo.bulk_upsert(db, user_a.id, _track_data(3))
        repo.bulk_upsert(db, user_b.id, _track_data(2))

        assert len(repo.get_by_user(db, user_a.id)) == 3
        assert len(repo.get_by_user(db, user_b.id)) == 2
