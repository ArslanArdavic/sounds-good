"""Build chat messages for playlist generation (RAG candidates → LLM)."""
from __future__ import annotations

from src.config import Settings, get_settings
from src.models.track import Track


SYSTEM_INSTRUCTIONS = """You are a music playlist curator. You receive a user request and a numbered list of candidate tracks from the user's personal library (each line: index, Spotify track ID, title, artist, duration in mm:ss).

Your task:
1. Choose an ordered subset of tracks that best matches the user's mood, genre, energy, and requested length.
2. Use ONLY Spotify track IDs from the provided list — never invent IDs.
3. Aim for a total duration close to what the user asked for (if they gave a time). If unclear, aim for about {default_min} minutes of music.
4. Respond with a single JSON object ONLY, no other text, using this exact shape:
{{"name": "<short playlist title>", "track_ids": ["<spotify_id>", ...]}}

The track_ids array must list Spotify IDs in playback order."""


class PromptBuilder:
    """Formats user text + candidate tracks into chat messages."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def build_messages(
        self,
        user_request: str,
        candidates: list[Track],
        feedback: str | None = None,
    ) -> list[dict[str, str]]:
        """Return OpenAI-style messages for Groq chat completions."""
        max_n = self._settings.playlist_generation_max_candidates
        max_chars = self._settings.playlist_generation_max_candidate_chars
        trimmed = candidates[:max_n]

        lines: list[str] = []
        block_len = 0
        for i, t in enumerate(trimmed, start=1):
            dur = _format_mm_ss(t.duration_ms)
            name = _shorten(t.name, 80)
            artist = _shorten(t.artist, 60)
            line = f"{i}. {t.spotify_track_id} | {name} | {artist} | {dur}"
            if block_len + len(line) + 1 > max_chars:
                break
            lines.append(line)
            block_len += len(line) + 1

        default_min = self._settings.default_target_duration_minutes
        system = SYSTEM_INSTRUCTIONS.format(default_min=default_min)

        user_parts: list[str] = [
            f"User request:\n{user_request.strip()}",
            "",
            "Candidate tracks (use only these IDs):",
            "\n".join(lines),
        ]
        if feedback:
            user_parts.extend(["", "Correction from previous attempt:", feedback])

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n".join(user_parts)},
        ]


def _shorten(text: str, max_len: int) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _format_mm_ss(duration_ms: int) -> str:
    total_sec = max(0, duration_ms // 1000)
    m, s = divmod(total_sec, 60)
    return f"{m:d}:{s:02d}"
