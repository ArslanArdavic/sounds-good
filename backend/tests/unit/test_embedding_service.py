"""Unit tests for EmbeddingService."""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.services.embedding_service import EmbeddingService


def _make_track(name: str = "Song", artist: str = "Artist", spotify_track_id: str = "t1"):
    """Build a lightweight Track-like object without touching the SQLAlchemy ORM."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        spotify_track_id=spotify_track_id,
        name=name,
        artist=artist,
        duration_ms=200_000,
        audio_features=None,
    )


@pytest.fixture
def mock_model():
    model = MagicMock()
    # encode returns a numpy array of shape (n, 384)
    def fake_encode(texts, convert_to_numpy=True):
        return np.random.rand(len(texts), 384).astype("float32")
    model.encode.side_effect = fake_encode
    return model


@pytest.fixture
def service(mock_model):
    svc = EmbeddingService()
    svc._model = mock_model
    return svc


class TestEncodeQuery:
    def test_returns_list_of_floats(self, service):
        result = service.encode_query("upbeat workout music")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_returns_384_dim_vector(self, service):
        result = service.encode_query("chill lo-fi beats")
        assert len(result) == 384

    def test_calls_model_encode_once(self, service, mock_model):
        service.encode_query("test")
        mock_model.encode.assert_called_once()


class TestEncodeTracks:
    def test_returns_one_vector_per_track(self, service):
        tracks = [_make_track(f"Song {i}", f"Artist {i}", f"t{i}") for i in range(5)]
        result = service.encode_tracks(tracks)
        assert len(result) == 5

    def test_each_vector_is_384_dims(self, service):
        tracks = [_make_track()]
        result = service.encode_tracks(tracks)
        assert len(result[0]) == 384

    def test_text_format_is_name_space_artist(self, service, mock_model):
        tracks = [_make_track("Bohemian Rhapsody", "Queen", "t1")]
        service.encode_tracks(tracks)
        texts_passed = mock_model.encode.call_args.args[0]
        assert texts_passed == ["Bohemian Rhapsody Queen"]

    def test_batch_text_order_matches_track_order(self, service, mock_model):
        tracks = [
            _make_track("Song A", "Artist A", "t1"),
            _make_track("Song B", "Artist B", "t2"),
            _make_track("Song C", "Artist C", "t3"),
        ]
        service.encode_tracks(tracks)
        texts_passed = mock_model.encode.call_args.args[0]
        assert texts_passed == ["Song A Artist A", "Song B Artist B", "Song C Artist C"]

    def test_returns_empty_for_empty_input(self, service, mock_model):
        result = service.encode_tracks([])
        assert result == []
        mock_model.encode.assert_not_called()


class TestLazyLoad:
    def test_model_not_loaded_at_init(self):
        svc = EmbeddingService()
        assert svc._model is None

    def test_model_loaded_on_first_encode(self):
        svc = EmbeddingService()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(1, 384).astype("float32")
        # SentenceTransformer is imported inside _get_model(), so patch at the source module
        with patch("sentence_transformers.SentenceTransformer", return_value=mock_model) as mock_cls:
            svc.encode_query("test")
            mock_cls.assert_called_once_with("all-MiniLM-L6-v2")

    def test_model_loaded_only_once_across_calls(self):
        svc = EmbeddingService()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(1, 384).astype("float32")
        with patch("sentence_transformers.SentenceTransformer", return_value=mock_model) as mock_cls:
            svc.encode_query("first call")
            svc.encode_query("second call")
            mock_cls.assert_called_once()
