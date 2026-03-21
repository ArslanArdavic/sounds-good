"""Service for syncing a user's Spotify library into the local database and vector index."""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.orm import Session

from src.clients.spotify_client import SPOTIFY_ADD_TRACKS_BATCH_SIZE, SpotifyClient
from src.models.playlist import Playlist
from src.models.user import User
from src.middleware.error_handler import ExternalServiceError, NotFoundError
from src.repositories.playlist_repository import PlaylistRepository
from src.repositories.track_repository import TrackRepository
from src.services.spotify_auth_service import SpotifyAuthService, get_spotify_auth_service
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)

# Exponential-backoff config for Spotify 429 / 5xx responses.
_INITIAL_BACKOFF = 1.0   # seconds
_MAX_BACKOFF = 64.0      # seconds
_MAX_RETRIES = 5

ProgressCallback = Callable[[int, int, int], Awaitable[None] | None]
"""Signature: (playlists_done, total_playlists, tracks_done)."""


def _is_client_error(exc: ExternalServiceError) -> bool:
    """Return True if the error is a non-retryable 4xx response (e.g. 403, 404)."""
    msg = str(exc)
    for code in ("returned 400", "returned 401", "returned 403", "returned 404"):
        if code in msg:
            return True
    return False


async def _with_backoff(coro_factory: Callable[[], Any]) -> Any:
    """Call ``coro_factory()`` repeatedly with exponential backoff on 429/5xx errors.

    4xx client errors (except 429) are re-raised immediately without retrying —
    they will not resolve on their own.

    Args:
        coro_factory: Zero-arg callable that returns a coroutine each time.

    Returns:
        The result of the first successful call.

    Raises:
        ExternalServiceError: Immediately on 4xx; after ``_MAX_RETRIES`` on 5xx/429.
    """
    backoff = _INITIAL_BACKOFF
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await coro_factory()
        except ExternalServiceError as exc:
            if _is_client_error(exc):
                raise  # 4xx — not transient, don't retry
            last_exc = exc
            logger.warning(
                "Spotify request failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt + 1,
                _MAX_RETRIES,
                exc,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)
    raise ExternalServiceError("Spotify", f"Max retries exceeded: {last_exc}")


class SpotifyService:
    """Orchestrates full library sync: fetch → store → embed."""

    def __init__(
        self,
        spotify_client: SpotifyClient | None = None,
        auth_service: SpotifyAuthService | None = None,
        track_repo: TrackRepository | None = None,
        playlist_repo: PlaylistRepository | None = None,
        vector_search: VectorSearchService | None = None,
    ) -> None:
        self._client = spotify_client or SpotifyClient()
        self._auth = auth_service or get_spotify_auth_service()
        self._tracks = track_repo or TrackRepository()
        self._playlists = playlist_repo or PlaylistRepository()
        self._vector = vector_search or VectorSearchService()

    async def sync_library(
        self,
        user_id: uuid.UUID,
        db: Session,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, int]:
        """Fetch all playlists and tracks from Spotify and index them locally.

        Pagination is handled automatically.  Audio features are fetched in
        batches of 100.  A 429 response from Spotify triggers exponential
        back-off and retry.

        Args:
            user_id: UUID of the user whose library to sync.
            db: Active SQLAlchemy session (caller controls commit).
            on_progress: Optional async or sync callable called after each
                playlist with signature ``(playlists_done, total_playlists,
                tracks_done)``.

        Returns:
            Dict with ``{"playlists_synced": N, "tracks_synced": M}``.
        """
        access_token = await self._auth.get_valid_access_token(user_id, db)

        # ------------------------------------------------------------------ #
        # 1. Fetch all playlists (paginated)
        # ------------------------------------------------------------------ #
        all_playlists: list[dict] = []
        offset = 0
        limit = 50
        while True:
            page = await _with_backoff(
                lambda o=offset: self._client.get_user_playlists(access_token, offset=o, limit=limit)
            )
            all_playlists.extend(page.get("items", []))
            if page.get("next") is None:
                break
            offset += limit

        total_playlists = len(all_playlists)
        all_tracks_data: list[dict] = []
        playlist_track_map: dict[str, list[str]] = {}  # spotify_playlist_id → [spotify_track_id]

        # ------------------------------------------------------------------ #
        # 2. Fetch tracks for each playlist (paginated)
        # ------------------------------------------------------------------ #
        for pl_idx, playlist in enumerate(all_playlists):
            sp_playlist_id: str = playlist["id"]
            playlist_name: str = playlist.get("name", "")
            playlist_track_map[sp_playlist_id] = []

            track_offset = 0
            track_limit = 50
            while True:
                try:
                    page = await _with_backoff(
                        lambda pid=sp_playlist_id, o=track_offset: self._client.get_playlist_tracks(
                            access_token, pid, offset=o, limit=track_limit
                        )
                    )
                except ExternalServiceError as exc:
                    # 403 = playlist the user doesn't own or collaborate on.
                    # Skip it rather than aborting the entire sync.
                    if "403" in str(exc):
                        logger.warning(
                            "Skipping playlist %r (%s) — access forbidden (403)",
                            playlist_name,
                            sp_playlist_id,
                        )
                        break
                    raise
                items = page.get("items", [])
                for item in items:
                    # /playlists/{id}/items returns track data under "item" key
                    # (the deprecated /tracks endpoint used "track")
                    track = item.get("item") if item else None
                    if track and track.get("id") and track.get("type") == "track":
                        sid = track["id"]
                        artists = track.get("artists", [])
                        artist_name = artists[0]["name"] if artists else "Unknown"
                        all_tracks_data.append(
                            {
                                "spotify_track_id": sid,
                                "name": track.get("name", ""),
                                "artist": artist_name,
                                "duration_ms": track.get("duration_ms", 0),
                                "audio_features": None,
                            }
                        )
                        playlist_track_map[sp_playlist_id].append(sid)

                if page.get("next") is None:
                    break
                track_offset += track_limit

            if playlist_track_map[sp_playlist_id]:
                logger.info(
                    "Fetched %d track(s) from playlist %r (%s)",
                    len(playlist_track_map[sp_playlist_id]),
                    playlist_name,
                    sp_playlist_id,
                )

            # Upsert playlist record
            self._playlists.upsert(db, user_id, sp_playlist_id, playlist_name)

            playlists_done = pl_idx + 1
            if on_progress is not None:
                result = on_progress(playlists_done, total_playlists, len(all_tracks_data))
                if asyncio.iscoroutine(result):
                    await result

        # ------------------------------------------------------------------ #
        # 3. Fetch audio features in batches of 100
        #    The /audio-features endpoint requires Extended Quota Mode on Spotify;
        #    if it returns 403 we skip it gracefully rather than aborting the sync.
        # ------------------------------------------------------------------ #
        unique_track_ids = list({t["spotify_track_id"] for t in all_tracks_data})
        features_by_id: dict[str, dict] = {}
        for i in range(0, len(unique_track_ids), 100):
            batch_ids = unique_track_ids[i : i + 100]
            try:
                features_batch = await _with_backoff(
                    lambda b=batch_ids: self._client.get_audio_features(access_token, b)
                )
                for f in features_batch:
                    if f and f.get("id"):
                        features_by_id[f["id"]] = f
            except ExternalServiceError as exc:
                if "403" in str(exc):
                    logger.warning(
                        "Audio features unavailable (403 — Extended Quota Mode required); "
                        "tracks will be stored without audio features."
                    )
                    break
                raise

        for track_data in all_tracks_data:
            track_data["audio_features"] = features_by_id.get(track_data["spotify_track_id"])

        # ------------------------------------------------------------------ #
        # 4. Deduplicate and store tracks
        # ------------------------------------------------------------------ #
        seen: set[str] = set()
        unique_tracks_data: list[dict] = []
        for td in all_tracks_data:
            if td["spotify_track_id"] not in seen:
                seen.add(td["spotify_track_id"])
                unique_tracks_data.append(td)

        upserted_tracks = self._tracks.bulk_upsert(db, user_id, unique_tracks_data)

        # ------------------------------------------------------------------ #
        # 5. Wire up playlist → track relationships
        # ------------------------------------------------------------------ #
        track_id_by_spotify: dict[str, uuid.UUID] = {
            t.spotify_track_id: t.id for t in upserted_tracks
        }
        all_db_playlists = self._playlists.get_by_user(db, user_id)
        playlist_obj_by_spotify: dict[str, Any] = {
            p.spotify_playlist_id: p for p in all_db_playlists if p.spotify_playlist_id
        }
        for sp_pl_id, sp_track_ids in playlist_track_map.items():
            playlist_obj = playlist_obj_by_spotify.get(sp_pl_id)
            if playlist_obj is None:
                continue
            pairs = [
                (track_id_by_spotify[sid], pos + 1)
                for pos, sid in enumerate(sp_track_ids)
                if sid in track_id_by_spotify
            ]
            self._playlists.add_tracks(db, playlist_obj.id, pairs)

        # ------------------------------------------------------------------ #
        # 6. Vector-index all tracks
        # ------------------------------------------------------------------ #
        self._vector.index_tracks(user_id, upserted_tracks)

        return {
            "playlists_synced": total_playlists,
            "tracks_synced": len(upserted_tracks),
        }

    async def save_playlist_to_spotify(
        self,
        db: Session,
        user: User,
        playlist: Playlist,
    ) -> Playlist:
        """Create a Spotify playlist, add tracks in batches, link the local row.

        Args:
            db: Active session (caller commits).
            user: Authenticated user (must own ``playlist``).
            playlist: Loaded playlist with ``playlist_tracks`` and nested ``track``.

        Returns:
            Playlist with ``spotify_playlist_id`` set and relations loaded.

        Raises:
            NotFoundError: If the playlist row could not be updated (should not
                happen if the caller validated ownership).
            ExternalServiceError: On Spotify API failures after retries.
        """
        ordered = sorted(playlist.playlist_tracks, key=lambda pt: pt.position)
        track_uris = [f"spotify:track:{pt.track.spotify_track_id}" for pt in ordered]

        access_token = await self._auth.get_valid_access_token(user.id, db)

        created = await _with_backoff(
            lambda: self._client.create_playlist(
                access_token,
                playlist.name,
                description="Created by Sounds Good",
                public=False,
            )
        )
        spotify_playlist_id: str = created["id"]

        for i in range(0, len(track_uris), SPOTIFY_ADD_TRACKS_BATCH_SIZE):
            batch = track_uris[i : i + SPOTIFY_ADD_TRACKS_BATCH_SIZE]
            await _with_backoff(
                lambda b=batch: self._client.add_tracks_to_playlist_batch(
                    access_token, spotify_playlist_id, b
                )
            )

        updated = self._playlists.link_spotify_playlist(
            db, playlist.id, user.id, spotify_playlist_id
        )
        if updated is None:
            raise NotFoundError("Playlist not found")
        reloaded = self._playlists.get_with_tracks(db, playlist.id)
        return reloaded if reloaded is not None else updated
