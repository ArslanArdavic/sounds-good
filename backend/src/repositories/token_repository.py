import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.spotify_token import SpotifyToken


class TokenRepository:
    """Data access layer for the SpotifyToken model."""

    def get_by_user_id(self, db: Session, user_id: uuid.UUID) -> SpotifyToken | None:
        """Return the stored token record for a user, or None."""
        return (
            db.query(SpotifyToken).filter(SpotifyToken.user_id == user_id).first()
        )

    def upsert(
        self,
        db: Session,
        user_id: uuid.UUID,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes,
        expires_at: datetime,
    ) -> SpotifyToken:
        """Create or update the SpotifyToken record for a user.

        Uses flush so the caller controls the transaction boundary.
        """
        token = self.get_by_user_id(db, user_id)
        if token is None:
            token = SpotifyToken(
                user_id=user_id,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
            )
            db.add(token)
        else:
            token.encrypted_access_token = encrypted_access_token
            token.encrypted_refresh_token = encrypted_refresh_token
            token.expires_at = expires_at
        db.flush()
        return token
