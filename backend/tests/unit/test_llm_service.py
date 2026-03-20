"""Unit tests for LLMService."""
import json
from unittest.mock import MagicMock

import pytest

from src.services.llm_service import LLMService, PlaylistLLMOutput


def test_generate_playlist_output_validates():
    client = MagicMock()
    client.chat_completion.return_value = '{"name": "Cool Mix", "track_ids": ["a", "b"]}'
    svc = LLMService(client=client)  # type: ignore[arg-type]
    out = svc.generate_playlist_output([{"role": "user", "content": "x"}])
    assert out.name == "Cool Mix"
    assert out.track_ids == ["a", "b"]


def test_generate_playlist_output_strips_markdown_fence():
    client = MagicMock()
    client.chat_completion.return_value = '```json\n{"name": "X", "track_ids": ["z"]}\n```'
    svc = LLMService(client=client)  # type: ignore[arg-type]
    out = svc.generate_playlist_output([])
    assert isinstance(out, PlaylistLLMOutput)


def test_generate_playlist_output_invalid_json_raises():
    client = MagicMock()
    client.chat_completion.return_value = "not json"
    svc = LLMService(client=client)  # type: ignore[arg-type]
    with pytest.raises(json.JSONDecodeError):
        svc.generate_playlist_output([])
