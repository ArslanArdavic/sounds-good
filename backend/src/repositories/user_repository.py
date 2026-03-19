import uuid

from sqlalchemy.orm import Session

from src.models.user import User


class UserRepository:
    """Data access layer for the User model."""

    def get_by_spotify_id(self, db: Session, spotify_id: str) -> User | None:
        """Return the user with the given Spotify user ID, or None."""
        return db.query(User).filter(User.spotify_id == spotify_id).first()

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> User | None:
        """Return the user with the given internal UUID, or None."""
        return db.get(User, user_id)

    def upsert(self, db: Session, spotify_id: str) -> User:
        """Return the existing user or create a new one for the given spotify_id.

        Uses flush (not commit) so the caller controls the transaction boundary.
        """
        user = self.get_by_spotify_id(db, spotify_id)
        if user is None:
            user = User(spotify_id=spotify_id)
            db.add(user)
            db.flush()  # Assigns user.id without committing
        return user
