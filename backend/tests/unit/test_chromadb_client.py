"""Unit tests for ChromaDBClient."""
import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from src.clients.chromadb_client import ChromaDBClient, _collection_name


@pytest.fixture
def mock_chroma_client():
    return MagicMock()


@pytest.fixture
def client(mock_chroma_client):
    with patch("src.clients.chromadb_client.chromadb.HttpClient", return_value=mock_chroma_client):
        with patch("src.clients.chromadb_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(chromadb_host="localhost", chromadb_port=8001)
            return ChromaDBClient()


class TestCollectionName:
    def test_uses_user_id_in_name(self):
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        name = _collection_name(uid)
        assert "12345678" in name

    def test_no_hyphens_in_name(self):
        uid = uuid.uuid4()
        name = _collection_name(uid)
        assert "-" not in name

    def test_prefixed_with_user(self):
        uid = uuid.uuid4()
        assert _collection_name(uid).startswith("user_")


class TestGetOrCreateCollection:
    def test_calls_get_or_create_with_correct_name(self, client, mock_chroma_client):
        uid = uuid.uuid4()
        client.get_or_create_collection(uid)
        mock_chroma_client.get_or_create_collection.assert_called_once()
        call_kwargs = mock_chroma_client.get_or_create_collection.call_args
        assert call_kwargs.kwargs["name"] == _collection_name(uid)

    def test_sets_cosine_distance_metadata(self, client, mock_chroma_client):
        client.get_or_create_collection(uuid.uuid4())
        call_kwargs = mock_chroma_client.get_or_create_collection.call_args
        assert call_kwargs.kwargs["metadata"] == {"hnsw:space": "cosine"}

    def test_returns_collection_object(self, client, mock_chroma_client):
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        result = client.get_or_create_collection(uuid.uuid4())
        assert result is mock_collection


class TestAddDocuments:
    def test_calls_upsert_with_correct_args(self, client):
        mock_collection = MagicMock()
        ids = ["t1", "t2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"name": "A"}, {"name": "B"}]
        client.add_documents(mock_collection, ids, embeddings, metadatas)
        mock_collection.upsert.assert_called_once_with(
            ids=ids, embeddings=embeddings, metadatas=metadatas
        )


class TestQuery:
    def test_returns_metadata_with_distances(self, client):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "metadatas": [[{"spotify_track_id": "t1"}, {"spotify_track_id": "t2"}]],
            "distances": [[0.1, 0.2]],
        }
        result = client.query(mock_collection, [0.1, 0.2], n_results=10)
        assert result == [
            {"spotify_track_id": "t1", "distance": 0.1},
            {"spotify_track_id": "t2", "distance": 0.2},
        ]

    def test_passes_n_results_and_includes(self, client):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"metadatas": [[]], "distances": [[]]}
        client.query(mock_collection, [0.5], n_results=42)
        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["n_results"] == 42
        assert "metadatas" in call_kwargs["include"]

    def test_returns_empty_on_empty_results(self, client):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"metadatas": [[]], "distances": [[]]}
        result = client.query(mock_collection, [0.0])
        assert result == []


class TestDeleteCollection:
    def test_calls_delete_with_correct_name(self, client, mock_chroma_client):
        uid = uuid.uuid4()
        client.delete_collection(uid)
        mock_chroma_client.delete_collection.assert_called_once_with(
            name=_collection_name(uid)
        )

    def test_no_op_when_collection_does_not_exist(self, client, mock_chroma_client):
        mock_chroma_client.delete_collection.side_effect = Exception("not found")
        uid = uuid.uuid4()
        client.delete_collection(uid)  # Should not raise
