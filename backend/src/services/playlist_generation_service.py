"""Service orchestrating RAG-based track retrieval for playlist generation."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.models.track import Track
from src.repositories.track_repository import TrackRepository
from src.services.vector_search_service import SearchResult, VectorSearchService

logger = logging.getLogger(__name__)


class PlaylistGenerationService:
    """Coordinates vector search, DB hydration, and optional audio-feature filtering.

    This service implements the retrieval stage of the RAG pipeline.  The LLM
    integration and playlist creation will be added in Phase 4.
    """

    def __init__(
        self,
        vector_search: VectorSearchService | None = None,
        track_repo: TrackRepository | None = None,
    ) -> None:
        self._vector = vector_search or VectorSearchService()
        self._tracks = track_repo or TrackRepository()

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
