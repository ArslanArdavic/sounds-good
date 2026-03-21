"""Parse and validate LLM JSON output for playlist generation."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.clients.llm_client import LLMClient


class PlaylistLLMOutput(BaseModel):
    """Expected JSON shape from the model."""

    name: str = Field(..., min_length=1, max_length=255)
    track_ids: list[str] = Field(..., min_length=1)


class LLMService:
    """Sends prompts to Groq and returns validated structured output."""

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or LLMClient()

    def generate_playlist_output(self, messages: list[dict[str, Any]]) -> PlaylistLLMOutput:
        """Call LLM and parse ``PlaylistLLMOutput``."""
        raw = self._complete_json(messages)
        data = self._parse_json_object(raw)
        try:
            return PlaylistLLMOutput.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"LLM output failed validation: {e}") from e

    def _complete_json(self, messages: list[dict[str, Any]]) -> str:
        try:
            return self._client.chat_completion(messages, json_mode=True)
        except Exception:
            return self._client.chat_completion(messages, json_mode=False)

    @staticmethod
    def _parse_json_object(text: str) -> Any:
        """Strip optional markdown fences and parse JSON."""
        cleaned = text.strip()
        fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", cleaned, re.IGNORECASE)
        if fence:
            cleaned = fence.group(1).strip()
        return json.loads(cleaned)
