"""Unit tests for PlaylistRepository."""
import uuid

import pytest

from src.models.user import User
from src.repositories.playlist_repository import PlaylistRepository
from src.repositories.track_repository import TrackRepository


@pytest.fixture
def user(db):
    u = User(spotify_id="pl_test_user")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def repo():
    return PlaylistRepository()


@pytest.fixture
def track_repo():
    return TrackRepository()


def _make_tracks(db, user_id, n=3):
    """Helper: insert n tracks and return them."""
    track_repo = TrackRepository()
    return track_repo.bulk_upsert(
        db,
        user_id,
        [
            {
                "spotify_track_id": f"track_{i:04d}",
                "name": f"Track {i}",
                "artist": f"Artist {i}",
                "duration_ms": 180_000,
                "audio_features": None,
            }
            for i in range(n)
        ],
    )


class TestUpsert:
    def test_creates_new_playlist(self, db, user, repo):
        pl = repo.upsert(db, user.id, "sp_pl_001", "My Playlist")
        assert pl.id is not None
        assert pl.spotify_playlist_id == "sp_pl_001"
        assert pl.name == "My Playlist"
        assert pl.user_id == user.id

    def test_updates_existing_playlist_name(self, db, user, repo):
        repo.upsert(db, user.id, "sp_pl_001", "Original Name")
        updated = repo.upsert(db, user.id, "sp_pl_001", "Updated Name")
        assert updated.name == "Updated Name"

    def test_no_duplicate_on_re_upsert(self, db, user, repo):
        repo.upsert(db, user.id, "sp_pl_001", "A")
        repo.upsert(db, user.id, "sp_pl_001", "B")
        playlists = repo.get_by_user(db, user.id)
        assert len(playlists) == 1

    def test_different_spotify_ids_create_separate_playlists(self, db, user, repo):
        repo.upsert(db, user.id, "sp_pl_001", "Playlist One")
        repo.upsert(db, user.id, "sp_pl_002", "Playlist Two")
        playlists = repo.get_by_user(db, user.id)
        assert len(playlists) == 2

    def test_same_spotify_id_different_users_are_independent(self, db, repo):
        user_a = User(spotify_id="user_alpha")
        user_b = User(spotify_id="user_beta")
        db.add_all([user_a, user_b])
        db.flush()

        pl_a = repo.upsert(db, user_a.id, "shared_id", "A's Playlist")
        pl_b = repo.upsert(db, user_b.id, "shared_id", "B's Playlist")
        assert pl_a.id != pl_b.id


class TestAddTracks:
    def test_adds_tracks_with_correct_positions(self, db, user, repo):
        from src.models.playlist import PlaylistTrack
        tracks = _make_tracks(db, user.id, 3)
        pl = repo.upsert(db, user.id, "sp_pl_001", "Test Playlist")

        pairs = [(t.id, i + 1) for i, t in enumerate(tracks)]
        repo.add_tracks(db, pl.id, pairs)

        pts = db.query(PlaylistTrack).filter_by(playlist_id=pl.id).order_by(PlaylistTrack.position).all()
        assert len(pts) == 3
        assert [pt.position for pt in pts] == [1, 2, 3]

    def test_replaces_existing_tracks_on_second_call(self, db, user, repo):
        from src.models.playlist import PlaylistTrack
        tracks = _make_tracks(db, user.id, 3)
        pl = repo.upsert(db, user.id, "sp_pl_001", "Test Playlist")

        repo.add_tracks(db, pl.id, [(tracks[0].id, 1), (tracks[1].id, 2)])
        repo.add_tracks(db, pl.id, [(tracks[2].id, 1)])

        pts = db.query(PlaylistTrack).filter_by(playlist_id=pl.id).all()
        assert len(pts) == 1
        assert pts[0].track_id == tracks[2].id

    def test_empty_track_list_clears_playlist(self, db, user, repo):
        from src.models.playlist import PlaylistTrack
        tracks = _make_tracks(db, user.id, 2)
        pl = repo.upsert(db, user.id, "sp_pl_001", "Test Playlist")
        repo.add_tracks(db, pl.id, [(t.id, i + 1) for i, t in enumerate(tracks)])

        repo.add_tracks(db, pl.id, [])
        pts = db.query(PlaylistTrack).filter_by(playlist_id=pl.id).all()
        assert pts == []
