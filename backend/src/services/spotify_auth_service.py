import secrets
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

from sqlalchemy.orm import Session

from src.clients.spotify_client import SpotifyClient, generate_pkce_pair
from src.middleware.error_handler import AuthenticationError
from src.models.user import User
from src.repositories.token_repository import TokenRepository
from src.repositories.user_repository import UserRepository
from src.utils.token_encryptor import TokenEncryptor

_PKCE_STATE_TTL_SECONDS = 600  # 10 minutes — longer than typical OAuth round-trip


class _PkceStateStore:
    """Thread-safe in-memory store mapping state -> code_verifier with TTL expiry.

    In production this should be replaced with a Redis-backed implementation.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, datetime]] = {}  # state -> (verifier, created_at)
        self._lock = Lock()

    def put(self, state: str, code_verifier: str) -> None:
        with self._lock:
            self._store[state] = (code_verifier, datetime.now(timezone.utc))

    def pop(self, state: str) -> str:
        """Retrieve and remove the verifier for state.

        Raises AuthenticationError if state is unknown or expired.
        """
        with self._lock:
            self._evict_expired()
            entry = self._store.pop(state, None)
        if entry is None:
            raise AuthenticationError("Invalid or expired OAuth state parameter")
        return entry[0]

    def _evict_expired(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=_PKCE_STATE_TTL_SECONDS)
        expired = [s for s, (_, created) in self._store.items() if created < cutoff]
        for s in expired:
            del self._store[s]


# Module-level singleton — shared across all requests in the same process.
_pkce_store = _PkceStateStore()


class SpotifyAuthService:
    """Orchestrates the Spotify OAuth PKCE flow and session token lifecycle."""

    def __init__(
        self,
        spotify_client: SpotifyClient,
        user_repo: UserRepository,
        token_repo: TokenRepository,
        encryptor: TokenEncryptor,
    ) -> None:
        self._client = spotify_client
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._encryptor = encryptor

    def generate_auth_url(self) -> tuple[str, str]:
        """Generate a Spotify authorization URL using PKCE.

        Returns:
            (url, state) — url is the full Spotify authorize URL the frontend
            should redirect to; state is the opaque CSRF/PKCE state token.
        """
        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(32)
        _pkce_store.put(state, code_verifier)
        url = self._client.build_auth_url(state=state, code_challenge=code_challenge)
        return url, state

    async def handle_callback(
        self, code: str, state: str, db: Session
    ) -> User:
        """Process the OAuth callback, persist tokens, and return the User.

        Args:
            code: Authorization code from Spotify.
            state: State parameter echoed back by Spotify — used to retrieve
                   the PKCE code_verifier.
            db: SQLAlchemy session (transaction is committed here).

        Returns:
            The upserted User ORM instance.

        Raises:
            AuthenticationError: If state is invalid/expired.
            ExternalServiceError: If Spotify API calls fail.
        """
        code_verifier = _pkce_store.pop(state)

        # Exchange code for tokens
        token_data = await self._client.exchange_code(code, code_verifier)
        access_token: str = token_data["access_token"]
        refresh_token: str = token_data["refresh_token"]
        expires_in: int = token_data["expires_in"]  # seconds, typically 3600

        # Fetch Spotify user profile to get the stable user ID
        spotify_user = await self._client.get_current_user(access_token)
        spotify_id: str = spotify_user["id"]

        # Persist user and encrypted tokens in a single transaction
        user = self._user_repo.upsert(db, spotify_id=spotify_id)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._token_repo.upsert(
            db,
            user_id=user.id,
            encrypted_access_token=self._encryptor.encrypt(access_token),
            encrypted_refresh_token=self._encryptor.encrypt(refresh_token),
            expires_at=expires_at,
        )
        db.commit()
        db.refresh(user)
        return user

    async def get_valid_access_token(
        self, user_id: uuid.UUID, db: Session
    ) -> str:
        """Return a valid (non-expired) Spotify access token for the given user.

        If the stored token is expired, refreshes it using the refresh token,
        updates the database, and returns the new access token.

        Args:
            user_id: Internal UUID of the user.
            db: SQLAlchemy session.

        Returns:
            Plaintext Spotify access token.

        Raises:
            AuthenticationError: If no token record exists for the user.
            ExternalServiceError: If the Spotify refresh request fails.
        """
        token_record = self._token_repo.get_by_user_id(db, user_id)
        if token_record is None:
            raise AuthenticationError("No Spotify token found — user must re-authenticate")

        if not token_record.is_expired:
            return self._encryptor.decrypt(token_record.encrypted_access_token)

        # Token is expired — refresh it
        refresh_token = self._encryptor.decrypt(token_record.encrypted_refresh_token)
        token_data = await self._client.refresh_access_token(refresh_token)

        new_access_token: str = token_data["access_token"]
        # Spotify may or may not issue a new refresh token
        new_refresh_token: str = token_data.get("refresh_token", refresh_token)
        expires_in: int = token_data["expires_in"]

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._token_repo.upsert(
            db,
            user_id=user_id,
            encrypted_access_token=self._encryptor.encrypt(new_access_token),
            encrypted_refresh_token=self._encryptor.encrypt(new_refresh_token),
            expires_at=expires_at,
        )
        db.commit()
        return new_access_token


def get_spotify_auth_service() -> SpotifyAuthService:
    """FastAPI dependency factory for SpotifyAuthService."""
    return SpotifyAuthService(
        spotify_client=SpotifyClient(),
        user_repo=UserRepository(),
        token_repo=TokenRepository(),
        encryptor=TokenEncryptor(),
    )
