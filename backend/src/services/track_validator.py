"""Ensure LLM-chosen Spotify IDs are from the candidate set."""
from __future__ import annotations


def validate_track_ids(
    chosen: list[str],
    allowed_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Return (valid_ordered, invalid_ids).

    Preserves order of *chosen* for valid IDs; drops duplicates after first
    occurrence. Invalid IDs are any string not in *allowed_ids*.
    """
    seen: set[str] = set()
    valid: list[str] = []
    invalid: list[str] = []
    for sid in chosen:
        if sid not in allowed_ids:
            invalid.append(sid)
            continue
        if sid in seen:
            continue
        seen.add(sid)
        valid.append(sid)
    return valid, invalid
