"""Service orchestrating RAG-based track retrieval for playlist generation."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import status
from groq import APIStatusError
from sqlalchemy.orm import Session

from src.config import get_settings
from src.middleware.error_handler import AppError
from src.models.playlist import Playlist
from src.models.track import Track
from src.repositories.playlist_repository import PlaylistRepository
from src.repositories.track_repository import TrackRepository
from src.services.duration_matcher import (
    duration_feedback,
    duration_within_tolerance,
    infer_target_duration_ms,
    total_duration_ms,
)
from src.services.llm_service import LLMService
from src.services.prompt_builder import PromptBuilder
from src.services.track_validator import validate_track_ids
from src.services.vector_search_service import SearchResult, VectorSearchService

logger = logging.getLogger(__name__)


class PlaylistGenerationService:
    """Coordinates RAG retrieval, LLM selection, validation, and playlist persistence."""

    def __init__(
        self,
        vector_search: VectorSearchService | None = None,
        track_repo: TrackRepository | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_service: LLMService | None = None,
        playlist_repo: PlaylistRepository | None = None,
    ) -> None:
        self._vector = vector_search or VectorSearchService()
        self._tracks = track_repo or TrackRepository()
        self._prompts = prompt_builder or PromptBuilder()
        self._llm = llm_service or LLMService()
        self._playlists = playlist_repo or PlaylistRepository()

    def generate_playlist(
        self,
        db: Session,
        user_id: uuid.UUID,
        user_text: str,
    ) -> Playlist:
        """Retrieve candidates, ask the LLM to curate, validate, and persist."""
        settings = get_settings()
        candidates = self.retrieve_tracks(db, user_id, user_text)
        if not candidates:
            raise AppError(
                "No matching tracks in your library for this request. "
                "Try syncing your library or describing different music.",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="no_candidates",
            )

        max_c = settings.playlist_generation_max_candidates
        candidates = candidates[:max_c]
        allowed_ids = {t.spotify_track_id for t in candidates}
        target_ms = infer_target_duration_ms(user_text, settings)

        feedback: str | None = None
        max_attempts = settings.playlist_generation_max_attempts
        last_issue: str | None = None

        for attempt in range(max_attempts):
            messages = self._prompts.build_messages(user_text, candidates, feedback)
            try:
                out = self._llm.generate_playlist_output(messages)
            except APIStatusError as e:
                # Retrying with longer prompts makes token-limit errors worse — fail fast.
                code = e.response.status_code if e.response is not None else None
                logger.warning("Groq APIStatusError %s: %s", code, e)
                if code == 413:
                    raise AppError(
                        "The playlist request is too large for your Groq plan (token limit). "
                        "Lower PLAYLIST_GENERATION_MAX_CANDIDATES (e.g. 60) or "
                        "PLAYLIST_GENERATION_MAX_CANDIDATE_CHARS in backend/.env.",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        error_code="groq_token_limit",
                    ) from e
                if code == 429:
                    raise AppError(
                        "Groq rate limit — wait a minute and try again.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        error_code="groq_rate_limit",
                    ) from e
                if code == 401:
                    raise AppError(
                        "Groq rejected the request — check GROQ_API_KEY.",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        error_code="groq_auth",
                    ) from e
                raise AppError(
                    f"Groq error ({code}): {str(e)[:400]}",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    error_code="groq_error",
                ) from e
            except Exception as e:
                logger.warning("LLM attempt %d failed: %s", attempt + 1, e)
                last_issue = str(e)[:500]
                feedback = (
                    "Your previous reply could not be parsed. Reply with a single JSON object only: "
                    '{"name": "...", "track_ids": ["...", ...]}'
                )
                continue

            valid_ids, invalid = validate_track_ids(out.track_ids, allowed_ids)
            if invalid:
                logger.warning(
                    "Dropped %d invalid Spotify track IDs (not in candidate list)",
                    len(invalid),
                )
            if not valid_ids:
                last_issue = "no valid track_ids after dropping unknown IDs"
                feedback = (
                    "Include at least one track_id copied exactly from the candidate list."
                )
                continue

            ordered = self._tracks.get_by_spotify_ids(db, user_id, valid_ids)
            if len(ordered) != len(valid_ids):
                last_issue = "track_ids not found in database"
                feedback = (
                    "Some track_ids were not found. Use only IDs from the candidate list."
                )
                continue

            total_ms = total_duration_ms(ordered)
            if not duration_within_tolerance(total_ms, target_ms, settings):
                if attempt < max_attempts - 1:
                    last_issue = "duration outside tolerance"
                    feedback = duration_feedback(total_ms, target_ms, settings)
                    continue
                logger.warning(
                    "Accepting playlist despite duration mismatch on final attempt "
                    "(total_ms=%s target_ms=%s)",
                    total_ms,
                    target_ms,
                )

            name = out.name.strip() if out.name else "Generated playlist"
            playlist = self._playlists.create_ai_playlist(db, user_id, name)
            pairs = [(t.id, i + 1) for i, t in enumerate(ordered)]
            self._playlists.add_tracks(db, playlist.id, pairs)
            db.flush()
            loaded = self._playlists.get_with_tracks(db, playlist.id)
            assert loaded is not None
            logger.info(
                "generate_playlist: user=%s attempts_used=%d tracks=%d",
                user_id,
                attempt + 1,
                len(ordered),
            )
            return loaded

        detail = " Try rephrasing your request."
        if last_issue:
            detail = f" Last issue: {last_issue}.{detail}"
        raise AppError(
            "Could not generate a valid playlist after several attempts." + detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="playlist_generation_failed",
        )

    def retrieve_tracks(
        self,
        db: Session,
        user_id: uuid.UUID,
        query: str,
        n_results: int | None = None,
        max_distance: float | None = None,
        audio_filters: dict[str, Any] | None = None,
    ) -> list[Track]:
        """Run semantic search and return full Track ORM objects.

        Pipeline: encode query → vector search → fetch from DB → optional
        audio-feature filtering.

        Args:
            db: Active SQLAlchemy session.
            user_id: UUID of the user whose library to search.
            query: Natural-language playlist description.
            n_results: Max results from vector search (defaults to service default).
            max_distance: Optional cosine-distance ceiling.
            audio_filters: Optional dict of audio-feature constraints.
                Keys are feature names (e.g. ``"energy"``, ``"tempo"``),
                values are ``{"min": float, "max": float}`` dicts.  Tracks
                outside the range on any specified feature are dropped.

        Returns:
            List of Track ORM objects ordered by semantic similarity.
        """
        search_results: list[SearchResult] = self._vector.search(
            user_id, query, n_results=n_results, max_distance=max_distance
        )

        if not search_results:
            return []

        spotify_ids = [r["spotify_track_id"] for r in search_results]
        tracks = self._tracks.get_by_spotify_ids(db, user_id, spotify_ids)

        if audio_filters:
            tracks = self._apply_audio_filters(tracks, audio_filters)

        logger.info(
            "retrieve_tracks: query=%r → %d vector hits → %d tracks returned",
            query,
            len(search_results),
            len(tracks),
        )
        return tracks

    @staticmethod
    def _apply_audio_filters(
        tracks: list[Track],
        filters: dict[str, Any],
    ) -> list[Track]:
        """Keep only tracks whose audio features satisfy all filter constraints."""
        filtered: list[Track] = []
        for track in tracks:
            features = _parse_audio_features(track.audio_features)
            if features is None:
                continue
            if _matches_filters(features, filters):
                filtered.append(track)
        return filtered


def _parse_audio_features(raw: str | None) -> dict[str, Any] | None:
    """Deserialize the JSON-encoded audio_features column."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _matches_filters(features: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Return True if *features* satisfies every constraint in *filters*."""
    for key, bounds in filters.items():
        value = features.get(key)
        if value is None:
            return False
        lo = bounds.get("min")
        hi = bounds.get("max")
        if lo is not None and value < lo:
            return False
        if hi is not None and value > hi:
            return False
    return True
