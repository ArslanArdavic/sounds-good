"""Infer target duration from user text and check ±tolerance."""
from __future__ import annotations

import re

from src.config import Settings, get_settings
from src.models.track import Track


def infer_target_duration_ms(user_text: str, settings: Settings | None = None) -> int:
    """Parse minutes/hours from natural language; default from settings."""
    s = settings or get_settings()
    default_ms = s.default_target_duration_minutes * 60 * 1000
    text = user_text.lower()

    # "2 hours", "1 hour", "90 minutes", "45 min", "60m"
    m = re.search(r"(\d+(?:\.\d+)?)\s*hours?", text)
    if m:
        return int(float(m.group(1)) * 60 * 60 * 1000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min\b|m\b)", text)
    if m:
        return int(float(m.group(1)) * 60 * 1000)
    m = re.search(r"\b(\d{2,3})\s*min\b", text)
    if m:
        val = int(m.group(1))
        if 10 <= val <= 300:
            return val * 60 * 1000

    return default_ms


def total_duration_ms(tracks: list[Track]) -> int:
    return sum(t.duration_ms for t in tracks)


def duration_within_tolerance(
    actual_ms: int,
    target_ms: int,
    settings: Settings | None = None,
) -> bool:
    s = settings or get_settings()
    tol = s.duration_tolerance_minutes * 60 * 1000
    return abs(actual_ms - target_ms) <= tol


def duration_feedback(
    actual_ms: int,
    target_ms: int,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    tol_min = s.duration_tolerance_minutes
    actual_min = actual_ms / 60_000
    target_min = target_ms / 60_000
    return (
        f"Total duration is about {actual_min:.0f} minutes but the user asked for "
        f"about {target_min:.0f} minutes (±{tol_min} minutes tolerance). "
        f"Add or remove tracks to get closer to the target length."
    )
