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
# Phase 1 needs user-read-private; Phases 2-5 need the rest.
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
