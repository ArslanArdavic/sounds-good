import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spotify_id: Mapped[str] = mapped_column(String(22), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    tracks: Mapped[list["Track"]] = relationship(  # type: ignore[name-defined]
        "Track", back_populates="user", cascade="all, delete-orphan"
    )
    playlists: Mapped[list["Playlist"]] = relationship(  # type: ignore[name-defined]
        "Playlist", back_populates="user", cascade="all, delete-orphan"
    )
    spotify_token: Mapped["SpotifyToken | None"] = relationship(  # type: ignore[name-defined]
        "SpotifyToken", back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} spotify_id={self.spotify_id!r}>"
