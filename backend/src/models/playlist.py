import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # Spotify source playlist ID (null for AI-generated playlists created in Phase 4+)
    spotify_playlist_id: Mapped[str | None] = mapped_column(String(22), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="playlists"
    )
    playlist_tracks: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistTrack.position"
    )

    def __repr__(self) -> str:
        return f"<Playlist id={self.id} name={self.name!r}>"


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playlists.id"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tracks.id"), nullable=False)

    playlist: Mapped["Playlist"] = relationship("Playlist", back_populates="playlist_tracks")
    track: Mapped["Track"] = relationship(  # type: ignore[name-defined]
        "Track", back_populates="playlist_tracks"
    )

    def __repr__(self) -> str:
        return f"<PlaylistTrack playlist_id={self.playlist_id} track_id={self.track_id} pos={self.position}>"
