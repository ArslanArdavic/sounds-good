"""Repository for Track CRUD and bulk cache operations."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.models.track import Track


class TrackRepository:
    """Handles all database operations for the Track model."""

    CACHE_TTL_HOURS = 24

    def get_by_user(self, db: Session, user_id: uuid.UUID) -> list[Track]:
        """Return all tracks belonging to a user.

        Args:
            db: Active database session.
            user_id: UUID of the owning user.

        Returns:
            List of Track ORM objects (may be empty).
        """
        return db.query(Track).filter(Track.user_id == user_id).all()

    def delete_stale(self, db: Session, user_id: uuid.UUID) -> int:
        """Delete tracks cached more than 24 hours ago for a user.

        Args:
            db: Active database session.
            user_id: UUID of the owning user.

        Returns:
            Number of rows deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.CACHE_TTL_HOURS)
        deleted = (
            db.query(Track)
            .filter(Track.user_id == user_id, Track.cached_at < cutoff)
            .delete(synchronize_session="fetch")
        )
        db.flush()
        return deleted

    def bulk_upsert(
        self,
        db: Session,
        user_id: uuid.UUID,
        tracks_data: list[dict],
    ) -> list[Track]:
        """Insert new tracks and update existing ones for a user.

        Stale tracks (older than 24 h) are removed first.  Matching is done on
        ``spotify_track_id`` — if a track with the same ID already exists for
        this user it is updated in-place; otherwise a new row is created.

        Args:
            db: Active database session.
            user_id: UUID of the owning user.
            tracks_data: List of dicts, each with keys:
                - spotify_track_id (str)
                - name (str)
                - artist (str)
                - duration_ms (int)
                - audio_features (dict | None, optional)

        Returns:
            List of upserted Track ORM objects.
        """
        self.delete_stale(db, user_id)

        existing: dict[str, Track] = {
            t.spotify_track_id: t
            for t in db.query(Track).filter(Track.user_id == user_id).all()
        }

        now = datetime.now(timezone.utc)
        upserted: list[Track] = []

        new_tracks: list[Track] = []
        for data in tracks_data:
            sid = data["spotify_track_id"]
            audio_raw = data.get("audio_features")
            audio_json = json.dumps(audio_raw) if audio_raw is not None else None

            if sid in existing:
                track = existing[sid]
                track.name = data["name"]
                track.artist = data["artist"]
                track.duration_ms = data["duration_ms"]
                track.audio_features = audio_json
                track.cached_at = now
                upserted.append(track)
            else:
                track = Track(
                    user_id=user_id,
                    spotify_track_id=sid,
                    name=data["name"],
                    artist=data["artist"],
                    duration_ms=data["duration_ms"],
                    audio_features=audio_json,
                    cached_at=now,
                )
                new_tracks.append(track)
                upserted.append(track)

        db.add_all(new_tracks)
        db.flush()
        return upserted
