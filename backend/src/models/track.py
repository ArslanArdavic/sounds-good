import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    spotify_track_id: Mapped[str] = mapped_column(
        String(22), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="tracks"
    )
    playlist_tracks: Mapped[list["PlaylistTrack"]] = relationship(  # type: ignore[name-defined]
        "PlaylistTrack", back_populates="track", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Track id={self.id} name={self.name!r} artist={self.artist!r}>"
