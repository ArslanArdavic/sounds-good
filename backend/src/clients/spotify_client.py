import base64
import hashlib
import os

import httpx

from src.config import get_settings
from src.middleware.error_handler import ExternalServiceError

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Spotify caps "Add items to playlist" at 100 URIs per request.
SPOTIFY_ADD_TRACKS_BATCH_SIZE = 100

# All documented Spotify Web API authorization scopes (space-separated for /authorize).
# See https://developer.spotify.com/documentation/web-api/concepts/scopes
SPOTIFY_SCOPES = " ".join(
    sorted(
        {
            "playlist-modify-private",
            "playlist-modify-public",
            "playlist-read-collaborative",
            "playlist-read-private",
            "user-library-modify",
            "user-library-read",
        }
    )
)


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

    async def get_user_playlists(
        self, access_token: str, offset: int = 0, limit: int = 50
    ) -> dict:
        """Fetch a page of the current user's playlists.

        Args:
            access_token: A valid Spotify access token.
            offset: Pagination offset (0-based).
            limit: Number of playlists per page (max 50).

        Returns:
            Spotify paging object with keys: items, total, next, offset, limit.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"offset": offset, "limit": limit}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/me/playlists", headers=headers, params=params
            )
        if response.status_code != 200:
            raise ExternalServiceError(
                "Spotify",
                f"GET /me/playlists returned {response.status_code}: {response.text}",
            )
        return response.json()

    async def get_playlist_tracks(
        self,
        access_token: str,
        playlist_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        """Fetch a page of items from a playlist using the current (non-deprecated) endpoint.

        Args:
            access_token: A valid Spotify access token.
            playlist_id: Spotify playlist ID.
            offset: Pagination offset (0-based).
            limit: Number of items per page (max 50).

        Returns:
            Spotify paging object with keys: items, total, next, offset, limit.
            Each item has a ``track`` sub-object with id, name, artists, duration_ms.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"offset": offset, "limit": limit}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items",
                headers=headers,
                params=params,
            )
        if response.status_code != 200:
            raise ExternalServiceError(
                "Spotify",
                f"GET /playlists/{playlist_id}/items returned {response.status_code}: {response.text}",
            )
        return response.json()

    async def get_audio_features(
        self, access_token: str, track_ids: list[str]
    ) -> list[dict]:
        """Fetch audio features for up to 100 tracks per call.

        Automatically batches lists longer than 100 into sequential requests.

        Args:
            access_token: A valid Spotify access token.
            track_ids: List of Spotify track IDs (strings, no URI prefix).

        Returns:
            Flat list of audio-feature dicts (same order as input).
            Tracks whose features are unavailable appear as ``None`` in Spotify's
            response and are filtered out here.

        Raises:
            ExternalServiceError: On any non-2xx response from Spotify.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        results: list[dict] = []
        batch_size = 100
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i : i + batch_size]
            params = {"ids": ",".join(batch)}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SPOTIFY_API_BASE}/audio-features",
                    headers=headers,
                    params=params,
                )
            if response.status_code != 200:
                raise ExternalServiceError(
                    "Spotify",
                    f"GET /audio-features returned {response.status_code}: {response.text}",
                )
            features = response.json().get("audio_features", [])
            results.extend(f for f in features if f is not None)
        return results

    async def create_playlist(
        self,
        access_token: str,
        name: str,
        *,
        description: str = "",
        public: bool = False,
    ) -> dict:
        """Create an empty playlist for the current user.

        Uses ``POST /v1/me/playlists`` (replaces deprecated
        ``POST /v1/users/{user_id}/playlists``). The token identifies the user.

        Returns:
            Spotify playlist object including ``id`` (22-char playlist id).

        Raises:
            ExternalServiceError: On any non-success response from Spotify.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {"name": name, "description": description, "public": public}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SPOTIFY_API_BASE}/me/playlists",
                headers=headers,
                json=body,
            )
        if response.status_code not in (200, 201):
            raise ExternalServiceError(
                "Spotify",
                f"POST /me/playlists returned {response.status_code}: {response.text}",
            )
        return response.json()

    async def add_tracks_to_playlist_batch(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        """Append up to ``SPOTIFY_ADD_TRACKS_BATCH_SIZE`` track URIs to a playlist.

        Args:
            access_token: Valid Spotify access token.
            playlist_id: Target playlist Spotify id.
            track_uris: ``spotify:track:...`` URIs (length must be ≤ batch size).

        Raises:
            ExternalServiceError: On any non-success response from Spotify.
            ValueError: If ``len(track_uris)`` exceeds ``SPOTIFY_ADD_TRACKS_BATCH_SIZE``.
        """
        if len(track_uris) > SPOTIFY_ADD_TRACKS_BATCH_SIZE:
            raise ValueError(
                f"At most {SPOTIFY_ADD_TRACKS_BATCH_SIZE} URIs per request; "
                f"got {len(track_uris)}"
            )
        if not track_uris:
            return
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        # Current API: POST /v1/playlists/{id}/items (replaces deprecated .../tracks).
        # https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items",
                headers=headers,
                json={"uris": track_uris},
            )
        if response.status_code not in (200, 201):
            raise ExternalServiceError(
                "Spotify",
                f"POST /playlists/{playlist_id}/items returned {response.status_code}: {response.text}",
            )

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
