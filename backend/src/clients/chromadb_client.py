"""Thin wrapper around the ChromaDB client for per-user vector collections."""
import uuid

import chromadb

from src.config import get_settings


def _collection_name(user_id: uuid.UUID) -> str:
    """Return a deterministic ChromaDB collection name for a user."""
    return f"user_{str(user_id).replace('-', '_')}"


class ChromaDBClient:
    """Manages ChromaDB collections for per-user track embeddings.

    One collection per user stores all track embeddings; this isolates data
    between users and allows efficient per-user operations.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )

    def get_or_create_collection(self, user_id: uuid.UUID) -> chromadb.Collection:
        """Return (or lazily create) the ChromaDB collection for a user.

        Args:
            user_id: UUID of the owning user.

        Returns:
            ChromaDB Collection object ready for add/query operations.
        """
        name = _collection_name(user_id)
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection: chromadb.Collection,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Upsert documents into a collection.

        Uses ``upsert`` so re-syncing a library updates existing vectors without
        creating duplicates.

        Args:
            collection: Target ChromaDB collection.
            ids: Unique document IDs (we use ``spotify_track_id`` values).
            embeddings: Pre-computed embedding vectors (one per document).
            metadatas: Metadata dicts stored alongside each embedding.
        """
        collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def query(
        self,
        collection: chromadb.Collection,
        query_embedding: list[float],
        n_results: int = 100,
    ) -> list[dict]:
        """Run a nearest-neighbour search against a collection.

        Args:
            collection: ChromaDB collection to search.
            query_embedding: Query vector (same dimensionality as stored vectors).
            n_results: Maximum number of results to return.

        Returns:
            List of metadata dicts for the nearest neighbours, ordered by
            ascending distance (most similar first).
        """
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "distances"],
        )
        metadatas_list: list[dict] = results.get("metadatas", [[]])[0]
        return metadatas_list

    def delete_collection(self, user_id: uuid.UUID) -> None:
        """Delete the collection for a user (used when triggering a full re-sync).

        If the collection does not exist the call is a no-op.

        Args:
            user_id: UUID of the owning user.
        """
        name = _collection_name(user_id)
        try:
            self._client.delete_collection(name=name)
        except Exception:
            pass
