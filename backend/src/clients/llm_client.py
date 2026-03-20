"""Thin wrapper around Groq chat completions with retries."""
from __future__ import annotations

import logging
import time
from typing import Any

from groq import Groq, APIStatusError

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Calls Groq OpenAI-compatible chat completions API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Groq(
            api_key=self._settings.groq_api_key,
            timeout=self._settings.groq_request_timeout_s,
        )

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool = True,
    ) -> str:
        """Return assistant message content (plain text / JSON string)."""
        kwargs: dict[str, Any] = {
            "model": self._settings.groq_model,
            "messages": messages,
            "temperature": 0.35,
            "max_tokens": 8192,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        max_retries = self._settings.groq_http_max_retries
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise RuntimeError("Groq returned empty assistant content")
                return content
            except APIStatusError as e:
                last_exc = e
                status = getattr(e, "status_code", None)
                if status in (429, 500, 502, 503) and attempt < max_retries - 1:
                    logger.warning(
                        "Groq APIStatusError (status=%s) attempt %d/%d — retrying in %.1fs",
                        status,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
                    continue
                raise
            except Exception as e:  # pragma: no cover — network flakiness
                last_exc = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "Groq request failed (%s) attempt %d/%d — retrying",
                        e,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
                    continue
                raise
        assert last_exc is not None
        raise last_exc
