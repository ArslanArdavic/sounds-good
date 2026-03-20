"""Repository for Playlist and PlaylistTrack CRUD operations."""
import uuid

from sqlalchemy.orm import Session

from src.models.playlist import Playlist, PlaylistTrack


class PlaylistRepository:
    """Handles all database operations for Playlist and PlaylistTrack models."""

    def get_by_user(self, db: Session, user_id: uuid.UUID) -> list[Playlist]:
        """Return all playlists belonging to a user.

        Args:
            db: Active database session.
            user_id: UUID of the owning user.

        Returns:
            List of Playlist ORM objects (may be empty).
        """
        return db.query(Playlist).filter(Playlist.user_id == user_id).all()

    def upsert(
        self,
        db: Session,
        user_id: uuid.UUID,
        spotify_playlist_id: str,
        name: str,
    ) -> Playlist:
        """Create or update a playlist identified by its Spotify playlist ID.

        If a playlist with the given ``spotify_playlist_id`` already exists for
        this user, its name is updated.  Otherwise a new row is created.

        Args:
            db: Active database session.
            user_id: UUID of the owning user.
            spotify_playlist_id: Spotify's unique playlist ID (22-char string).
            name: Display name of the playlist.

        Returns:
            The created or updated Playlist ORM object.
        """
        playlist = (
            db.query(Playlist)
            .filter(
                Playlist.user_id == user_id,
                Playlist.spotify_playlist_id == spotify_playlist_id,
            )
            .first()
        )

        if playlist is None:
            playlist = Playlist(
                user_id=user_id,
                spotify_playlist_id=spotify_playlist_id,
                name=name,
            )
            db.add(playlist)
        else:
            playlist.name = name

        db.flush()
        return playlist

    def add_tracks(
        self,
        db: Session,
        playlist_id: uuid.UUID,
        track_ids_with_positions: list[tuple[uuid.UUID, int]],
    ) -> None:
        """Replace the track list for a playlist.

        Deletes all existing PlaylistTrack rows for this playlist then inserts
        the provided tracks at their given positions.

        Args:
            db: Active database session.
            playlist_id: UUID of the local Playlist record.
            track_ids_with_positions: List of (track_id, position) tuples.
                ``position`` should be 1-based and unique within the playlist.
        """
        db.query(PlaylistTrack).filter(
            PlaylistTrack.playlist_id == playlist_id
        ).delete(synchronize_session="fetch")

        new_entries = [
            PlaylistTrack(playlist_id=playlist_id, track_id=track_id, position=pos)
            for track_id, pos in track_ids_with_positions
        ]
        db.add_all(new_entries)
        db.flush()
