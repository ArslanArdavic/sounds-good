"""Service combining ChromaDBClient and EmbeddingService for track indexing and search."""
from __future__ import annotations

import uuid
from typing import TypedDict

from src.clients.chromadb_client import ChromaDBClient
from src.models.track import Track
from src.services.embedding_service import EmbeddingService

DEFAULT_N_RESULTS = 1000


class SearchResult(TypedDict):
    """A single vector-search hit with metadata and similarity score."""

    spotify_track_id: str
    name: str
    artist: str
    duration_ms: int
    distance: float


class VectorSearchService:
    """Orchestrates embedding generation and ChromaDB operations for track search.

    Each user has an isolated ChromaDB collection. Tracks are indexed with their
    ``spotify_track_id`` as the document ID so upserts are idempotent.
    """

    def __init__(
        self,
        chroma_client: ChromaDBClient | None = None,
        embedding_service: EmbeddingService | None = None,
        default_n_results: int = DEFAULT_N_RESULTS,
        max_distance: float | None = None,
    ) -> None:
        self._chroma = chroma_client or ChromaDBClient()
        self._embeddings = embedding_service or EmbeddingService()
        self._default_n_results = default_n_results
        self._max_distance = max_distance

    def index_tracks(self, user_id: uuid.UUID, tracks: list[Track]) -> None:
        """Encode tracks and upsert them into the user's ChromaDB collection.

        Args:
            user_id: UUID of the owning user.
            tracks: List of Track ORM objects to index.
        """
        if not tracks:
            return

        embeddings = self._embeddings.encode_tracks(tracks)
        ids = [t.spotify_track_id for t in tracks]
        metadatas = [
            {
                "spotify_track_id": t.spotify_track_id,
                "name": t.name,
                "artist": t.artist,
                "duration_ms": t.duration_ms,
            }
            for t in tracks
        ]

        collection = self._chroma.get_or_create_collection(user_id)
        self._chroma.add_documents(collection, ids, embeddings, metadatas)

    def search(
        self,
        user_id: uuid.UUID,
        query_text: str,
        n_results: int | None = None,
        max_distance: float | None = None,
    ) -> list[SearchResult]:
        """Find the most semantically similar tracks to a query.

        Args:
            user_id: UUID of the user whose library to search.
            query_text: Free-text description (e.g. "upbeat workout music").
            n_results: Maximum number of results. Falls back to the instance
                default (1000) when ``None``.
            max_distance: Optional cosine-distance ceiling.  Results further
                than this threshold are dropped.  Falls back to the instance
                default when ``None``.

        Returns:
            List of :class:`SearchResult` dicts ordered by ascending distance
            (most similar first).
        """
        effective_n = self._default_n_results if n_results is None else n_results
        effective_max = self._max_distance if max_distance is None else max_distance

        query_embedding = self._embeddings.encode_query(query_text)
        collection = self._chroma.get_or_create_collection(user_id)
        raw = self._chroma.query(collection, query_embedding, n_results=effective_n)

        results: list[SearchResult] = []
        for r in raw:
            sid = r.get("spotify_track_id")
            if not sid:
                continue
            dist: float = r.get("distance", 1.0)
            if effective_max is not None and dist > effective_max:
                continue
            results.append(
                SearchResult(
                    spotify_track_id=sid,
                    name=r.get("name", ""),
                    artist=r.get("artist", ""),
                    duration_ms=r.get("duration_ms", 0),
                    distance=dist,
                )
            )
        return results

    def clear_user_tracks(self, user_id: uuid.UUID) -> None:
        """Delete and recreate the user's ChromaDB collection (full re-sync).

        Args:
            user_id: UUID of the user whose collection to reset.
        """
        self._chroma.delete_collection(user_id)
        self._chroma.get_or_create_collection(user_id)
