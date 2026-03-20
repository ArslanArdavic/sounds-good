"""Unit tests for VectorSearchService."""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from src.services.vector_search_service import VectorSearchService


def _make_track(spotify_track_id: str = "t1", name: str = "Song", artist: str = "Artist"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        spotify_track_id=spotify_track_id,
        name=name,
        artist=artist,
        duration_ms=200_000,
    )


@pytest.fixture
def mock_chroma():
    mock = MagicMock()
    mock.get_or_create_collection.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_embeddings():
    mock = MagicMock()
    mock.encode_tracks.return_value = [[0.1, 0.2], [0.3, 0.4]]
    mock.encode_query.return_value = [0.5, 0.6]
    return mock


@pytest.fixture
def service(mock_chroma, mock_embeddings):
    return VectorSearchService(chroma_client=mock_chroma, embedding_service=mock_embeddings)


class TestIndexTracks:
    def test_calls_encode_tracks(self, service, mock_embeddings):
        user_id = uuid.uuid4()
        tracks = [_make_track("t1"), _make_track("t2")]
        service.index_tracks(user_id, tracks)
        mock_embeddings.encode_tracks.assert_called_once_with(tracks)

    def test_calls_get_or_create_collection(self, service, mock_chroma):
        user_id = uuid.uuid4()
        service.index_tracks(user_id, [_make_track()])
        mock_chroma.get_or_create_collection.assert_called_once_with(user_id)

    def test_calls_add_documents_with_matching_ids(self, service, mock_chroma, mock_embeddings):
        user_id = uuid.uuid4()
        tracks = [_make_track("t1"), _make_track("t2")]
        mock_embeddings.encode_tracks.return_value = [[0.1], [0.2]]
        collection = mock_chroma.get_or_create_collection.return_value

        service.index_tracks(user_id, tracks)

        # add_documents is called with positional args: (collection, ids, embeddings, metadatas)
        call_args = mock_chroma.add_documents.call_args
        passed_collection, passed_ids, passed_embeddings, _ = call_args.args
        assert passed_collection is collection
        assert passed_ids == ["t1", "t2"]
        assert passed_embeddings == [[0.1], [0.2]]

    def test_metadata_contains_required_fields(self, service, mock_chroma, mock_embeddings):
        user_id = uuid.uuid4()
        track = _make_track("t1", "Bohemian Rhapsody", "Queen")
        mock_embeddings.encode_tracks.return_value = [[0.1]]
        service.index_tracks(user_id, [track])

        _, _, _, metadatas = mock_chroma.add_documents.call_args.args
        assert metadatas[0]["spotify_track_id"] == "t1"
        assert metadatas[0]["name"] == "Bohemian Rhapsody"
        assert metadatas[0]["artist"] == "Queen"
        assert "duration_ms" in metadatas[0]

    def test_no_op_for_empty_track_list(self, service, mock_chroma, mock_embeddings):
        service.index_tracks(uuid.uuid4(), [])
        mock_embeddings.encode_tracks.assert_not_called()
        mock_chroma.add_documents.assert_not_called()


class TestSearch:
    def test_calls_encode_query(self, service, mock_embeddings):
        service.search(uuid.uuid4(), "upbeat workout music")
        mock_embeddings.encode_query.assert_called_once_with("upbeat workout music")

    def test_calls_query_with_encoded_vector(self, service, mock_chroma, mock_embeddings):
        user_id = uuid.uuid4()
        mock_embeddings.encode_query.return_value = [0.9, 0.8]
        collection = mock_chroma.get_or_create_collection.return_value
        mock_chroma.query.return_value = []

        service.search(user_id, "test", n_results=50)

        mock_chroma.query.assert_called_once_with(
            collection, [0.9, 0.8], n_results=50
        )

    def test_returns_spotify_track_ids(self, service, mock_chroma):
        mock_chroma.query.return_value = [
            {"spotify_track_id": "t1", "name": "A"},
            {"spotify_track_id": "t2", "name": "B"},
        ]
        result = service.search(uuid.uuid4(), "test")
        assert result == ["t1", "t2"]

    def test_filters_metadata_without_spotify_track_id(self, service, mock_chroma):
        mock_chroma.query.return_value = [
            {"spotify_track_id": "t1"},
            {"name": "No ID"},
        ]
        result = service.search(uuid.uuid4(), "test")
        assert result == ["t1"]

    def test_returns_empty_for_no_results(self, service, mock_chroma):
        mock_chroma.query.return_value = []
        result = service.search(uuid.uuid4(), "test")
        assert result == []


class TestClearUserTracks:
    def test_calls_delete_then_create(self, service, mock_chroma):
        user_id = uuid.uuid4()
        service.clear_user_tracks(user_id)

        mock_chroma.delete_collection.assert_called_once_with(user_id)
        mock_chroma.get_or_create_collection.assert_called_once_with(user_id)

    def test_delete_called_before_create(self, service, mock_chroma):
        call_order = []
        mock_chroma.delete_collection.side_effect = lambda *_: call_order.append("delete")
        mock_chroma.get_or_create_collection.side_effect = lambda *_: call_order.append("create")

        service.clear_user_tracks(uuid.uuid4())
        assert call_order == ["delete", "create"]
