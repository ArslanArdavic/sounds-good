"""Service for generating text embeddings from track metadata."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from src.models.track import Track

MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    """Generates dense vector embeddings for tracks and free-text queries.

    The sentence-transformers model is lazy-loaded on the first encode call to
    avoid blocking application startup.
    """

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    @staticmethod
    def _track_to_text(track: Track) -> str:
        """Produce the text representation used for embedding a track.

        Format: ``"<name> <artist>"`` — simple and effective for music search.
        """
        return f"{track.name} {track.artist}"

    def encode_tracks(self, tracks: list[Track]) -> list[list[float]]:
        """Generate embeddings for a batch of tracks.

        Args:
            tracks: List of Track ORM objects.

        Returns:
            List of embedding vectors in the same order as ``tracks``.
            Each vector is a list of floats (384 dims for all-MiniLM-L6-v2).
        """
        if not tracks:
            return []
        texts = [self._track_to_text(t) for t in tracks]
        model = self._get_model()
        vectors = model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    def encode_query(self, text: str) -> list[float]:
        """Generate an embedding for a free-text query.

        Args:
            text: The user's natural-language playlist description.

        Returns:
            Single embedding vector as a list of floats.
        """
        model = self._get_model()
        vector = model.encode([text], convert_to_numpy=True)[0]
        return vector.tolist()
