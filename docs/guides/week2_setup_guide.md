# Week 2 Setup Guide — Sounds Good

## Phase 1: Authentication & User Management

**Goal:** Implement Spotify OAuth with PKCE, encrypted token storage, JWT sessions, and a fully working login flow end-to-end.

---

## Table of Contents

1. [Week 1 Recap & Current State](#1-week-1-recap--current-state)
2. [Pre-flight Checks](#2-pre-flight-checks)
3. [Step 1 — Fix Alembic & Run Initial Migration](#3-step-1--fix-alembic--run-initial-migration)
4. [Step 2 — Token Encryptor](#4-step-2--token-encryptor)
5. [Step 3 — Spotify Client](#5-step-3--spotify-client)
6. [Step 4 — Repositories](#6-step-4--repositories)
7. [Step 5 — Spotify Auth Service](#7-step-5--spotify-auth-service)
8. [Step 6 — Wire Up Auth Controller](#8-step-6--wire-up-auth-controller)
9. [Step 7 — Frontend Updates](#9-step-7--frontend-updates)
10. [Step 8 — Tests](#10-step-8--tests)
11. [Step 9 — Manual End-to-End Verification](#11-step-9--manual-end-to-end-verification)
12. [Acceptance Checklist](#12-acceptance-checklist)

---

## 1. Week 1 Recap & Current State

The following is already in place from Week 1 and **does not need to be recreated**:

| File | Status |
|---|---|
| `backend/src/main.py` | FastAPI app with CORS + error handlers registered |
| `backend/src/config.py` | Pydantic-Settings with all env vars (Spotify, Groq, DB, etc.) |
| `backend/src/models/database.py` | SQLAlchemy engine, `Base`, `get_db` session dependency |
| `backend/src/models/user.py` | `User` ORM model (id, spotify_id, created_at, relationships) |
| `backend/src/models/spotify_token.py` | `SpotifyToken` ORM model with `is_expired` property |
| `backend/src/models/track.py` | `Track` ORM model (Phase 2 use) |
| `backend/src/models/playlist.py` | `Playlist` + `PlaylistTrack` ORM models (Phase 4 use) |
| `backend/src/schemas/user_schema.py` | `UserResponse` Pydantic schema |
| `backend/src/middleware/auth_middleware.py` | `create_access_token()` + `get_current_user()` dependency |
| `backend/src/middleware/error_handler.py` | Full exception hierarchy + FastAPI handlers |
| `backend/src/controllers/auth_controller.py` | `/login` + `/callback` stubs (501); `/me` is live |
| `backend/tests/conftest.py` | `client`, `db`, `settings` fixtures with in-memory test DB |
| `frontend/src/pages/LoginPage.tsx` | "Connect with Spotify" UI |
| `frontend/src/pages/CallbackPage.tsx` | Exchanges OAuth code for JWT, navigates to `/sync` |
| `frontend/src/hooks/useAuth.ts` | JWT in `localStorage`, React Query for `/auth/me` |
| `frontend/src/services/api.ts` | Axios instance with `Bearer` token interceptor |
| `frontend/src/components/ProtectedRoute.tsx` | Redirects unauthenticated users to `/` |

**What is missing / stubbed:**

- `backend/alembic/env.py` — `target_metadata = None`, not wired to models (no migrations can run)
- `backend/src/utils/` — directory exists but empty
- `backend/src/clients/` — directory exists but empty
- `backend/src/repositories/` — directory exists but empty
- `backend/src/services/` — directory exists but empty
- `/auth/login` and `/auth/callback` return `HTTP 501`
- Frontend `CallbackPage` does not forward the `state` param to the backend
- `LoginPage` does not display `?error=` query param messages on redirect-back

---

## 2. Pre-flight Checks

Before writing any code, confirm the Week 1 baseline is working.

```bash
cd backend

# Activate the virtual environment
source $(poetry env info --path)/bin/activate

# Start the server
uvicorn src.main:app --reload --port 8000
```

In a second terminal:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "environment": "development", "timestamp": "2026-03-19T..."}
```

If the server fails to start, common causes:
- Missing `.env` file — copy `backend/.env.example` to `backend/.env` and fill in real values
- Missing `SECRET_KEY` or `ENCRYPTION_KEY` — see Appendix for how to generate them
- Poetry environment not activated — re-run `source $(poetry env info --path)/bin/activate`

---

## 3. Step 1 — Fix Alembic & Run Initial Migration

### Why

`alembic/env.py` was generated with `target_metadata = None`. Until it is wired to `Base.metadata`, `alembic revision --autogenerate` cannot detect the ORM models, and `alembic upgrade head` will run empty migrations.

### 3.1 Wire `env.py` to the SQLAlchemy models

Replace the entire contents of `backend/alembic/env.py`:

```python
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base so that all models registered against it are visible to autogenerate.
# The side-effect imports in main.py (track, playlist, etc.) are reproduced here.
from src.models.database import Base
import src.models.user          # noqa: F401
import src.models.spotify_token # noqa: F401
import src.models.track         # noqa: F401
import src.models.playlist      # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Allow DATABASE_URL to be overridden by the environment variable so that
# `alembic upgrade head` works without editing alembic.ini.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

> **Note on `render_as_batch=True`:** SQLite does not support `ALTER TABLE` natively. Alembic's batch mode works around this by recreating tables. This flag is harmless on PostgreSQL.

### 3.2 Set the database URL in `alembic.ini`

Open `backend/alembic.ini` and update the `sqlalchemy.url` line:

```ini
sqlalchemy.url = sqlite:///./sounds_good.db
```

This is only used as a fallback. The `env.py` above reads `DATABASE_URL` from the environment first, so this value is used only for local SQLite runs without a `.env` file loaded.

### 3.3 Generate the initial migration

```bash
cd backend
# Ensure .env is loaded so DATABASE_URL is available
export $(grep -v '^#' .env | xargs)

poetry run alembic revision --autogenerate -m "create initial tables"
```

You should see a new file created at `backend/alembic/versions/<hash>_create_initial_tables.py`. Open it and verify it contains `CREATE TABLE` operations for `users`, `spotify_tokens`, `tracks`, `playlists`, and `playlist_tracks`.

### 3.4 Apply the migration

```bash
poetry run alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> <hash>, create initial tables
```

Verify the database was created:
```bash
ls -lh sounds_good.db
```

### 3.5 Check migration status at any time

```bash
poetry run alembic current   # shows which revision the DB is at
poetry run alembic history   # lists all migrations
```

---

## 4. Step 2 — Token Encryptor

### What it does

`TokenEncryptor` wraps Python's `cryptography.fernet.Fernet` to provide symmetric encryption for Spotify access and refresh tokens before they are persisted to the database. Fernet guarantees that a message encrypted cannot be manipulated or read without the key.

### 4.1 Generate an encryption key (one-time setup)

If you haven't already generated `ENCRYPTION_KEY`, run:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (e.g. `3cJ7...=`) into `backend/.env` as `ENCRYPTION_KEY=<value>`.

> **Important:** The key must be exactly 32 URL-safe base64-encoded bytes. Do not truncate or modify it. Store it securely — losing it means all stored tokens become unreadable.

### 4.2 Create `backend/src/utils/__init__.py`

```python
```

(Empty file — marks the directory as a Python package.)

### 4.3 Create `backend/src/utils/token_encryptor.py`

```python
from cryptography.fernet import Fernet, InvalidToken

from src.config import get_settings


class TokenEncryptor:
    """Symmetric encryption wrapper for Spotify OAuth tokens.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) with the key from settings.
    The key must be a valid Fernet key — generate one with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self) -> None:
        settings = get_settings()
        key = settings.encryption_key
        # Accept both str and bytes — Fernet requires bytes
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a string token and return the ciphertext bytes."""
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes and return the original string token.

        Raises ValueError if the ciphertext is invalid or the key is wrong.
        """
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise ValueError("Token decryption failed — invalid ciphertext or wrong key") from exc
```

---

## 5. Step 3 — Spotify Client

### What it does

`SpotifyClient` is a thin async HTTP client over Spotify's Accounts and Web API endpoints. It is responsible only for transport — no business logic lives here. All methods raise `ExternalServiceError` on non-2xx responses so that callers do not need to inspect raw HTTP status codes.

### 5.1 Create `backend/src/clients/__init__.py`

```python
```

### 5.2 Create `backend/src/clients/spotify_client.py`

```python
import base64
import hashlib
import os

import httpx

from src.config import get_settings
from src.middleware.error_handler import ExternalServiceError

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# All scopes requested upfront so users never need to re-authenticate.
# Phase 1 needs user-read-private; Phases 2–5 need the rest.
SPOTIFY_SCOPES = " ".join([
    "user-read-private",
    "user-read-email",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
])


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 encoding without padding (RFC 7636)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair.

    Returns:
        (code_verifier, code_challenge) — both are URL-safe base64 strings.
    """
    code_verifier = _b64url_encode(os.urandom(64))
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = _b64url_encode(digest)
    return code_verifier, code_challenge


class SpotifyClient:
    """Async HTTP client for Spotify Accounts API and Web API."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def build_auth_url(self, state: str, code_challenge: str) -> str:
        """Build the Spotify authorization URL for the PKCE flow.

        Args:
            state: Random opaque value for CSRF protection.
            code_challenge: SHA-256 hash of the code_verifier (base64url, no padding).

        Returns:
            Full authorization URL to redirect the user to.
        """
        params = {
            "response_type": "code",
            "client_id": self._settings.spotify_client_id,
            "scope": SPOTIFY_SCOPES,
            "redirect_uri": self._settings.spotify_redirect_uri,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }
        request = httpx.Request("GET", SPOTIFY_AUTHORIZE_URL, params=params)
        return str(request.url)

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            code: Authorization code received from the Spotify callback.
            code_verifier: The original PKCE verifier (not the challenge).

        Returns:
            Token response dict with keys: access_token, refresh_token,
            expires_in, token_type, scope.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._settings.spotify_redirect_uri,
            "client_id": self._settings.spotify_client_id,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(SPOTIFY_TOKEN_URL, data=payload)
        return self._parse_token_response(response)

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Obtain a new access token using a stored refresh token.

        Args:
            refresh_token: The decrypted Spotify refresh token.

        Returns:
            Token response dict. Note: Spotify may or may not return a new
            refresh_token — if absent, the existing one remains valid.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._settings.spotify_client_id,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(SPOTIFY_TOKEN_URL, data=payload)
        return self._parse_token_response(response)

    async def get_current_user(self, access_token: str) -> dict:
        """Fetch the authenticated user's Spotify profile.

        Args:
            access_token: A valid (non-expired) Spotify access token.

        Returns:
            Spotify user object with at minimum: id, display_name, email.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SPOTIFY_API_BASE}/me", headers=headers)
        if response.status_code != 200:
            raise ExternalServiceError(
                "Spotify",
                f"GET /me returned {response.status_code}: {response.text}",
            )
        return response.json()

    @staticmethod
    def _parse_token_response(response: httpx.Response) -> dict:
        """Parse a Spotify token endpoint response, raising on errors."""
        if response.status_code != 200:
            try:
                detail = response.json().get("error_description", response.text)
            except Exception:
                detail = response.text
            raise ExternalServiceError(
                "Spotify",
                f"Token request failed ({response.status_code}): {detail}",
            )
        return response.json()
```

---

## 6. Step 4 — Repositories

Repositories encapsulate all database access for a single model. They receive a `Session` from the caller (the service layer) rather than creating their own, keeping transactions under service control.

### 6.1 Create `backend/src/repositories/__init__.py`

```python
```

### 6.2 Create `backend/src/repositories/user_repository.py`

```python
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
```

### 6.3 Create `backend/src/repositories/token_repository.py`

```python
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
```

---

## 7. Step 5 — Spotify Auth Service

### What it does

`SpotifyAuthService` is the heart of Phase 1. It orchestrates the entire OAuth PKCE flow:

1. **`generate_auth_url()`** — creates a PKCE verifier/challenge pair and a random `state`, stores `state → verifier` in memory, and delegates URL construction to `SpotifyClient`.
2. **`handle_callback()`** — retrieves the verifier by `state`, calls `SpotifyClient.exchange_code()`, fetches the Spotify user profile, upserts `User` and `SpotifyToken` records, and returns the `User` object.
3. **`get_valid_access_token()`** — checks whether the stored token is expired and refreshes it transparently before returning the plaintext access token.

### PKCE State Store

For Phase 1 (development), PKCE verifiers are stored in a module-level dictionary keyed by the opaque `state` value. Entries older than 10 minutes are discarded on every lookup to prevent memory leaks.

> **Production upgrade path:** Replace `_PkceStateStore` with a Redis-backed equivalent in Phase 6. The service interface does not change — only the store implementation.

### 7.1 Create `backend/src/services/__init__.py`

```python
```

### 7.2 Create `backend/src/services/spotify_auth_service.py`

```python
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

from sqlalchemy.orm import Session

from src.clients.spotify_client import SpotifyClient, generate_pkce_pair
from src.middleware.error_handler import AuthenticationError, ExternalServiceError
from src.models.user import User
from src.repositories.token_repository import TokenRepository
from src.repositories.user_repository import UserRepository
from src.utils.token_encryptor import TokenEncryptor

_PKCE_STATE_TTL_SECONDS = 600  # 10 minutes — longer than typical OAuth round-trip


class _PkceStateStore:
    """Thread-safe in-memory store mapping state → code_verifier with TTL expiry.

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
```

---

## 8. Step 6 — Wire Up Auth Controller

Replace the entire contents of `backend/src/controllers/auth_controller.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.middleware.auth_middleware import create_access_token, get_current_user
from src.middleware.error_handler import AuthenticationError
from src.models.database import get_db
from src.models.user import User
from src.schemas.user_schema import UserResponse
from src.services.spotify_auth_service import SpotifyAuthService, get_spotify_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login(
    auth_service: SpotifyAuthService = Depends(get_spotify_auth_service),
) -> dict[str, str]:
    """Generate a Spotify authorization URL and return it to the frontend.

    The frontend is responsible for redirecting the user to this URL.
    The state parameter is embedded in the URL; the frontend must pass it
    back verbatim when calling /auth/callback.
    """
    url, _state = auth_service.generate_auth_url()
    return {"url": url}


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    auth_service: SpotifyAuthService = Depends(get_spotify_auth_service),
) -> dict[str, str]:
    """Handle the Spotify OAuth callback.

    Spotify redirects the user to the frontend /callback page with ?code=&state=.
    The frontend forwards these query params to this endpoint.

    Returns a signed JWT that the frontend stores and uses for subsequent requests.
    """
    if not code or not state:
        raise AuthenticationError("Missing code or state parameter")

    user = await auth_service.handle_callback(code=code, state=state, db=db)
    access_token = create_access_token(user.id)
    return {"access_token": access_token}


@router.post("/logout")
def logout() -> dict[str, str]:
    """Signal logout. The frontend is responsible for clearing the stored JWT.

    This endpoint exists so future server-side session invalidation (e.g. token
    blocklist) can be added without changing the frontend contract.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
```

### Why the `state` isn't returned in `/login`

The Spotify authorization URL already contains the `state` as a query parameter. When Spotify redirects back to `http://localhost:3000/callback?code=X&state=Y`, the `state` is automatically present in the URL the frontend receives. The frontend reads `state` from `useSearchParams()` and forwards it to `/auth/callback`. There is no need to return `state` separately from `/login`.

---

## 9. Step 7 — Frontend Updates

### 9.1 Update `frontend/src/pages/CallbackPage.tsx`

The current version does not forward the `state` query parameter to the backend. Spotify includes `state` in the callback URL, and the backend now requires it to look up the PKCE verifier.

Replace the `useEffect` body:

{% raw %}
```typescript
import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import api from '../services/api'
import { useAuth } from '../hooks/useAuth'

export default function CallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setToken } = useAuth()
  const hasRun = useRef(false)

  useEffect(() => {
    if (hasRun.current) return
    hasRun.current = true

    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const error = searchParams.get('error')

    if (error || !code || !state) {
      navigate('/?error=access_denied', { replace: true })
      return
    }

    api
      .get<{ access_token: string }>(`/auth/callback?code=${code}&state=${state}`)
      .then(({ data }) => {
        setToken(data.access_token)
        navigate('/sync', { replace: true })
      })
      .catch((err: unknown) => {
        const status = axios.isAxiosError(err) ? err.response?.status : null
        if (status === 401) {
          navigate('/?error=auth_failed', { replace: true })
        } else {
          navigate('/?error=server_error', { replace: true })
        }
      })
  }, [])

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4">
      <MusicBars />
      <p className="text-sm" style={{ color: 'var(--text)' }}>
        Connecting your Spotify account…
      </p>
    </div>
  )
}

function MusicBars() {
  return (
    <div className="flex gap-1 items-end h-10">
      {[14, 22, 10, 18, 14].map((h, i) => (
        <span
          key={i}
          className="w-1.5 bg-spotify-green rounded-full animate-bounce"
          style={{ height: `${h}px`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  )
}
```
{% endraw %}

**Key change:** `state` is now extracted from `searchParams` and appended to the `/auth/callback` request. If `state` is missing (e.g. the user navigated directly to `/callback`), the page redirects to `/?error=access_denied`.

### 9.2 Update `frontend/src/pages/LoginPage.tsx`

The current `LoginPage` does not react to `?error=` query params. After auth failures (e.g. user denies Spotify access), `CallbackPage` redirects to `/?error=access_denied`. Update `LoginPage` to read and display these messages:

{% raw %}
```typescript
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import api from '../services/api'

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: 'Spotify access was denied. Please try again and accept the permissions.',
  auth_failed: 'Authentication failed. Please try again.',
  server_error: 'A server error occurred. Please try again in a moment.',
  not_implemented: 'This feature is not yet available.',
}

export default function LoginPage() {
  const [searchParams] = useSearchParams()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(
    () => {
      const errorParam = searchParams.get('error')
      return errorParam ? (ERROR_MESSAGES[errorParam] ?? 'An error occurred. Please try again.') : null
    },
  )

  const handleConnect = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await api.get<{ url: string }>('/auth/login')
      window.location.href = data.url
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError('Could not connect to Spotify. Please try again.')
      } else {
        setError('Something went wrong. Please try again.')
      }
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 py-20">
      <div className="w-full max-w-sm text-center">
        <MusicIcon />

        <h1 className="text-4xl font-semibold tracking-tight mt-6 mb-3" style={{ color: 'var(--text-h)' }}>
          Sounds Good
        </h1>
        <p className="text-base mb-10" style={{ color: 'var(--text)' }}>
          Generate playlists from your Spotify library using AI — only tracks you already own.
        </p>

        <button
          onClick={handleConnect}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-3 px-6 py-3.5 rounded-full bg-spotify-green text-white font-medium text-base transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
        >
          <SpotifyIcon />
          {isLoading ? 'Connecting…' : 'Connect with Spotify'}
        </button>

        {error && (
          <p className="mt-4 text-sm text-red-500">{error}</p>
        )}

        <p className="mt-8 text-xs" style={{ color: 'var(--text)' }}>
          We only read your playlists. We never modify or delete anything without your explicit action.
        </p>
      </div>
    </div>
  )
}

function MusicIcon() {
  return (
    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-spotify-green/10">
      <svg className="w-8 h-8 text-spotify-green" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z" />
      </svg>
    </div>
  )
}

function SpotifyIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
    </svg>
  )
}
```
{% endraw %}

---

## 10. Step 8 — Tests

All tests go into the `backend/tests/` directory. The existing `conftest.py` provides `client`, `db`, and `settings` fixtures — use them directly.

### 10.1 Unit tests for `TokenEncryptor`

Create `backend/tests/unit/test_token_encryptor.py`:

```python
import pytest
from cryptography.fernet import Fernet

from src.utils.token_encryptor import TokenEncryptor


@pytest.fixture
def encryptor(monkeypatch):
    """TokenEncryptor instance using a freshly-generated test key."""
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    # Clear the lru_cache so the new env var is picked up
    from src.config import get_settings
    get_settings.cache_clear()
    yield TokenEncryptor()
    get_settings.cache_clear()


def test_encrypt_returns_bytes(encryptor):
    result = encryptor.encrypt("some_token")
    assert isinstance(result, bytes)


def test_round_trip(encryptor):
    plaintext = "spotify_access_token_abc123"
    assert encryptor.decrypt(encryptor.encrypt(plaintext)) == plaintext


def test_different_ciphertexts_for_same_input(encryptor):
    """Fernet uses a random IV so each encryption produces a unique ciphertext."""
    token = "same_token"
    assert encryptor.encrypt(token) != encryptor.encrypt(token)


def test_decrypt_wrong_key_raises(monkeypatch):
    key_a = Fernet.generate_key().decode()
    key_b = Fernet.generate_key().decode()

    monkeypatch.setenv("ENCRYPTION_KEY", key_a)
    from src.config import get_settings
    get_settings.cache_clear()
    enc_a = TokenEncryptor()

    monkeypatch.setenv("ENCRYPTION_KEY", key_b)
    get_settings.cache_clear()
    enc_b = TokenEncryptor()

    ciphertext = enc_a.encrypt("secret_token")
    with pytest.raises(ValueError, match="decryption failed"):
        enc_b.decrypt(ciphertext)

    get_settings.cache_clear()


def test_decrypt_tampered_bytes_raises(encryptor):
    ciphertext = encryptor.encrypt("real_token")
    tampered = ciphertext[:-4] + b"xxxx"
    with pytest.raises(ValueError):
        encryptor.decrypt(tampered)
```

### 10.2 Unit tests for `SpotifyAuthService`

Create `backend/tests/unit/test_spotify_auth_service.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.middleware.error_handler import AuthenticationError


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    from src.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_spotify_client():
    client = MagicMock()
    client.build_auth_url.return_value = "https://accounts.spotify.com/authorize?code_challenge=abc"
    client.exchange_code = AsyncMock(return_value={
        "access_token": "access_abc",
        "refresh_token": "refresh_xyz",
        "expires_in": 3600,
    })
    client.get_current_user = AsyncMock(return_value={"id": "spotify_user_123"})
    client.refresh_access_token = AsyncMock(return_value={
        "access_token": "new_access_token",
        "expires_in": 3600,
    })
    return client


@pytest.fixture
def service(mock_spotify_client):
    from src.repositories.user_repository import UserRepository
    from src.repositories.token_repository import TokenRepository
    from src.utils.token_encryptor import TokenEncryptor
    from src.services.spotify_auth_service import SpotifyAuthService

    return SpotifyAuthService(
        spotify_client=mock_spotify_client,
        user_repo=UserRepository(),
        token_repo=TokenRepository(),
        encryptor=TokenEncryptor(),
    )


def test_generate_auth_url_returns_url_and_state(service):
    url, state = service.generate_auth_url()
    assert url.startswith("https://accounts.spotify.com/authorize")
    assert len(state) > 20


def test_generate_auth_url_unique_states(service):
    _, state1 = service.generate_auth_url()
    _, state2 = service.generate_auth_url()
    assert state1 != state2


@pytest.mark.asyncio
async def test_handle_callback_creates_user_and_token(service, db):
    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)
    assert user.spotify_id == "spotify_user_123"
    assert user.id is not None


@pytest.mark.asyncio
async def test_handle_callback_invalid_state_raises(service, db):
    with pytest.raises(AuthenticationError):
        await service.handle_callback(code="auth_code", state="bad_state", db=db)


@pytest.mark.asyncio
async def test_handle_callback_state_can_only_be_used_once(service, db):
    _, state = service.generate_auth_url()
    await service.handle_callback(code="auth_code", state=state, db=db)
    # Using same state a second time should fail
    with pytest.raises(AuthenticationError):
        await service.handle_callback(code="auth_code", state=state, db=db)


@pytest.mark.asyncio
async def test_get_valid_access_token_non_expired(service, db):
    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)

    token = await service.get_valid_access_token(user.id, db)
    assert token == "access_abc"
    # Spotify client should NOT have been called for a refresh
    service._client.refresh_access_token.assert_not_called()


@pytest.mark.asyncio
async def test_get_valid_access_token_expired_refreshes(service, db):
    from src.repositories.token_repository import TokenRepository
    from src.utils.token_encryptor import TokenEncryptor

    _, state = service.generate_auth_url()
    user = await service.handle_callback(code="auth_code", state=state, db=db)

    # Force the token to appear expired in the DB
    encryptor = TokenEncryptor()
    token_repo = TokenRepository()
    token_repo.upsert(
        db,
        user_id=user.id,
        encrypted_access_token=encryptor.encrypt("old_access"),
        encrypted_refresh_token=encryptor.encrypt("refresh_xyz"),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.commit()

    new_token = await service.get_valid_access_token(user.id, db)
    assert new_token == "new_access_token"
    service._client.refresh_access_token.assert_called_once_with("refresh_xyz")
```

### 10.3 Integration tests for `AuthController`

Create `backend/tests/integration/test_auth_controller.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    from src.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_login_returns_spotify_url(client):
    """GET /auth/login should return a Spotify authorization URL."""
    mock_service = MagicMock()
    mock_service.generate_auth_url.return_value = (
        "https://accounts.spotify.com/authorize?client_id=x&state=abc",
        "abc",
    )

    from src.controllers.auth_controller import router
    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/login")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "accounts.spotify.com" in data["url"]


def test_callback_missing_code_returns_401(client):
    """GET /auth/callback without code param should return 401."""
    response = client.get("/auth/callback?state=some_state")
    assert response.status_code in (401, 422)


def test_callback_missing_state_returns_422(client):
    """GET /auth/callback without state param should return 422 (validation error)."""
    response = client.get("/auth/callback?code=some_code")
    assert response.status_code in (401, 422)


def test_callback_invalid_state_returns_401(client):
    """GET /auth/callback with unknown state should return 401."""
    mock_service = MagicMock()
    mock_service.handle_callback = AsyncMock(
        side_effect=__import__("src.middleware.error_handler", fromlist=["AuthenticationError"]).AuthenticationError(
            "Invalid or expired OAuth state parameter"
        )
    )

    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/callback?code=some_code&state=bad_state")
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_callback_success_returns_access_token(client):
    """GET /auth/callback with valid code+state should return a JWT."""
    import uuid
    from src.models.user import User
    from src.services.spotify_auth_service import get_spotify_auth_service
    from src.main import app

    fake_user = MagicMock(spec=User)
    fake_user.id = uuid.uuid4()

    mock_service = MagicMock()
    mock_service.handle_callback = AsyncMock(return_value=fake_user)

    app.dependency_overrides[get_spotify_auth_service] = lambda: mock_service
    response = client.get("/auth/callback?code=real_code&state=real_state")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 20  # JWT is a non-trivial string


def test_me_unauthenticated_returns_401(client):
    """GET /auth/me without a Bearer token should return 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_authenticated_returns_user(client, db):
    """GET /auth/me with a valid JWT should return the user profile."""
    from src.middleware.auth_middleware import create_access_token
    from src.repositories.user_repository import UserRepository

    user_repo = UserRepository()
    user = user_repo.upsert(db, spotify_id="test_spotify_id_999")
    db.commit()

    token = create_access_token(user.id)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["spotify_id"] == "test_spotify_id_999"


def test_logout_returns_200(client):
    """POST /auth/logout should always return 200."""
    response = client.post("/auth/logout")
    assert response.status_code == 200
```

### 10.4 Run all tests

```bash
cd backend
poetry run pytest tests/ -v
```

Expected output (all green):
```
tests/unit/test_token_encryptor.py::test_encrypt_returns_bytes PASSED
tests/unit/test_token_encryptor.py::test_round_trip PASSED
tests/unit/test_token_encryptor.py::test_different_ciphertexts_for_same_input PASSED
tests/unit/test_token_encryptor.py::test_decrypt_wrong_key_raises PASSED
tests/unit/test_token_encryptor.py::test_decrypt_tampered_bytes_raises PASSED
tests/unit/test_spotify_auth_service.py::test_generate_auth_url_returns_url_and_state PASSED
tests/unit/test_spotify_auth_service.py::test_generate_auth_url_unique_states PASSED
tests/unit/test_spotify_auth_service.py::test_handle_callback_creates_user_and_token PASSED
tests/unit/test_spotify_auth_service.py::test_handle_callback_invalid_state_raises PASSED
tests/unit/test_spotify_auth_service.py::test_handle_callback_state_can_only_be_used_once PASSED
tests/unit/test_spotify_auth_service.py::test_get_valid_access_token_non_expired PASSED
tests/unit/test_spotify_auth_service.py::test_get_valid_access_token_expired_refreshes PASSED
tests/integration/test_auth_controller.py::test_login_returns_spotify_url PASSED
tests/integration/test_auth_controller.py::test_callback_missing_code_returns_401 PASSED
tests/integration/test_auth_controller.py::test_callback_missing_state_returns_422 PASSED
tests/integration/test_auth_controller.py::test_callback_invalid_state_returns_401 PASSED
tests/integration/test_auth_controller.py::test_callback_success_returns_access_token PASSED
tests/integration/test_auth_controller.py::test_me_unauthenticated_returns_401 PASSED
tests/integration/test_auth_controller.py::test_me_authenticated_returns_user PASSED
tests/integration/test_auth_controller.py::test_logout_returns_200 PASSED
```

Run with coverage to verify the 80% target:
```bash
poetry run pytest tests/ --cov=src --cov-report=term-missing
```

---

## 11. Step 9 — Manual End-to-End Verification

### 11.1 Start both servers

**Terminal 1 — Backend:**
```bash
cd backend
source $(poetry env info --path)/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Frontend will be at `http://localhost:5173` (Vite default) or `http://localhost:3000`.

### 11.2 Verify `/auth/login` returns a real Spotify URL

```bash
curl http://localhost:8000/auth/login
```

Expected response:
```json
{
  "url": "https://accounts.spotify.com/authorize?response_type=code&client_id=YOUR_ID&scope=...&redirect_uri=...&state=RANDOM&code_challenge_method=S256&code_challenge=HASH"
}
```

Verify the URL contains all of:
- `code_challenge_method=S256`
- `code_challenge=` (a base64url string)
- `state=` (a random string)
- `scope=` containing `user-read-private`

### 11.3 Complete the OAuth flow in the browser

1. Open `http://localhost:5173` in your browser.
2. Click "Connect with Spotify".
3. You will be redirected to Spotify's login page.
4. Log in and authorize the app.
5. Spotify redirects you to `http://localhost:3000/callback?code=X&state=Y`.
6. The `CallbackPage` sends `GET /auth/callback?code=X&state=Y` to the backend.
7. The backend exchanges the code, creates a user, and returns a JWT.
8. The frontend stores the JWT and navigates to `/sync`.

### 11.4 Verify the database was populated

```bash
cd backend
sqlite3 sounds_good.db ".tables"
# Should show: alembic_version  playlist_tracks  playlists  spotify_tokens  tracks  users

sqlite3 sounds_good.db "SELECT id, spotify_id, created_at FROM users;"
# Should show your Spotify user ID

sqlite3 sounds_good.db "SELECT id, user_id, expires_at FROM spotify_tokens;"
# Should show a row with your user's UUID
```

### 11.5 Verify `/auth/me` with the stored JWT

Copy the JWT from `localStorage` in your browser's DevTools (Application → Local Storage → `auth_token`), then:

```bash
curl -H "Authorization: Bearer <your_jwt_here>" http://localhost:8000/auth/me
```

Expected response:
```json
{
  "id": "...",
  "spotify_id": "your_spotify_id",
  "created_at": "2026-03-19T..."
}
```

### 11.6 Verify token refresh (optional manual test)

To test the refresh path without waiting an hour, temporarily force the token to expire directly in the database:

```bash
sqlite3 sounds_good.db \
  "UPDATE spotify_tokens SET expires_at = datetime('now', '-2 hours');"
```

Then call any protected endpoint that uses `get_valid_access_token()` (Phase 2 will provide this; for now you can verify by calling the service directly via a test or the FastAPI interactive docs at `http://localhost:8000/docs`).

---

## 12. Acceptance Checklist

All Phase 1 acceptance criteria from the implementation plan:

- [ ] **User can authenticate via Spotify OAuth** — clicking "Connect with Spotify" completes the full PKCE OAuth flow and lands on `/sync`
- [ ] **Tokens are encrypted and securely stored** — `spotify_tokens` table stores `LargeBinary` ciphertext, never plaintext
- [ ] **Session persists across page refreshes** — JWT in `localStorage` + React Query re-fetches `/auth/me` on mount
- [ ] **Token refresh works automatically** — `get_valid_access_token()` calls `refresh_access_token()` when `is_expired` is `True`
- [ ] **OAuth failure (access denied) is handled** — `CallbackPage` navigates to `/?error=access_denied`, `LoginPage` displays the message
- [ ] **Invalid/expired state is rejected with 401** — `_pkce_store.pop()` raises `AuthenticationError` for unknown states
- [ ] **All tests pass** — `poetry run pytest tests/ -v` is all green
- [ ] **Initial DB migration applied** — `alembic current` shows `head`

### New files created this week

```
backend/alembic/env.py                          (modified)
backend/alembic/versions/<hash>_create_initial_tables.py  (generated)
backend/src/utils/__init__.py
backend/src/utils/token_encryptor.py
backend/src/clients/__init__.py
backend/src/clients/spotify_client.py
backend/src/repositories/__init__.py
backend/src/repositories/user_repository.py
backend/src/repositories/token_repository.py
backend/src/services/__init__.py
backend/src/services/spotify_auth_service.py
backend/src/controllers/auth_controller.py      (modified)
backend/tests/unit/test_token_encryptor.py
backend/tests/unit/test_spotify_auth_service.py
backend/tests/integration/test_auth_controller.py
frontend/src/pages/CallbackPage.tsx             (modified)
frontend/src/pages/LoginPage.tsx                (modified)
```

### Git commit

```bash
git add .
git commit -m "feat(auth): implement Spotify OAuth PKCE flow with encrypted token storage"
```

---

## Appendix

### Generating required secret keys

```bash
# SECRET_KEY — used to sign JWTs
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY — used by Fernet to encrypt Spotify tokens
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add both to `backend/.env`.

### OAuth flow diagram

```
Browser                  Frontend             Backend              Spotify
  |                         |                    |                     |
  |-- click "Connect" -->   |                    |                     |
  |                         |-- GET /auth/login ->|                     |
  |                         |                    |-- generate PKCE --  |
  |                         |<-- { url } --------|                     |
  |<-- redirect to url --   |                    |                     |
  |                                                                     |
  |---------- GET accounts.spotify.com/authorize ---------------------->|
  |<--------- redirect to /callback?code=X&state=Y -------------------|
  |                         |                    |                     |
  |-- load /callback -->    |                    |                     |
  |                         |-- GET /auth/callback?code=X&state=Y ---->|
  |                         |                    |-- POST /token ------>|
  |                         |                    |<-- access_token -----|
  |                         |                    |-- GET /v1/me ------->|
  |                         |                    |<-- { id } ----------|
  |                         |                    |-- upsert user/token -|
  |                         |<-- { access_token: JWT } ---------------|
  |                         |-- store JWT in localStorage              |
  |                         |-- navigate to /sync                      |
```

### Common errors

| Error | Cause | Fix |
|---|---|---|
| `KeyError: ENCRYPTION_KEY` | Missing env var | Add `ENCRYPTION_KEY=<fernet_key>` to `backend/.env` |
| `Invalid or expired OAuth state parameter` | State TTL (10 min) exceeded | Complete the OAuth flow within 10 minutes |
| `alembic: No such table: users` | Migration not applied | Run `poetry run alembic upgrade head` |
| `INVALID_CLIENT: Invalid redirect URI` | Spotify app redirect URI mismatch | Add `http://localhost:3000/callback` in Spotify Developer Dashboard |
| `422 Unprocessable Entity` on `/auth/callback` | Missing `state` query param | Ensure `CallbackPage.tsx` passes `state` from `useSearchParams()` |
| `Fernet key must be 32 url-safe base64-encoded bytes` | Truncated or wrong format key | Regenerate with `Fernet.generate_key().decode()` |

### Spotify Developer Dashboard setup

In [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard):

1. Open your app → Edit Settings
2. Add to **Redirect URIs**: `http://localhost:3000/callback`
3. Save changes

The redirect URI in your `backend/.env` (`SPOTIFY_REDIRECT_URI`) must exactly match what is registered in the dashboard.
