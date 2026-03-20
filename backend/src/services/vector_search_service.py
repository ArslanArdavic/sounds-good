"""Service combining ChromaDBClient and EmbeddingService for track indexing and search."""
from __future__ import annotations

import uuid

from src.clients.chromadb_client import ChromaDBClient
from src.models.track import Track
from src.services.embedding_service import EmbeddingService


class VectorSearchService:
    """Orchestrates embedding generation and ChromaDB operations for track search.

    Each user has an isolated ChromaDB collection. Tracks are indexed with their
    ``spotify_track_id`` as the document ID so upserts are idempotent.
    """

    def __init__(
        self,
        chroma_client: ChromaDBClient | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._chroma = chroma_client or ChromaDBClient()
        self._embeddings = embedding_service or EmbeddingService()

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
        n_results: int = 100,
    ) -> list[str]:
        """Find the most semantically similar tracks to a query.

        Args:
            user_id: UUID of the user whose library to search.
            query_text: Free-text description (e.g. "upbeat workout music").
            n_results: Maximum number of results to return.

        Returns:
            List of ``spotify_track_id`` strings ordered by similarity
            (most similar first).
        """
        query_embedding = self._embeddings.encode_query(query_text)
        collection = self._chroma.get_or_create_collection(user_id)
        results = self._chroma.query(collection, query_embedding, n_results=n_results)
        return [r["spotify_track_id"] for r in results if "spotify_track_id" in r]

    def clear_user_tracks(self, user_id: uuid.UUID) -> None:
        """Delete and recreate the user's ChromaDB collection (full re-sync).

        Args:
            user_id: UUID of the user whose collection to reset.
        """
        self._chroma.delete_collection(user_id)
        self._chroma.get_or_create_collection(user_id)
