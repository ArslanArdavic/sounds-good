"""Unit tests for PromptBuilder."""
import uuid
from types import SimpleNamespace

from src.services.prompt_builder import PromptBuilder


def _track(sid: str, name: str = "N", artist: str = "A", duration_ms: int = 180_000):
    return SimpleNamespace(
        id=uuid.uuid4(),
        spotify_track_id=sid,
        name=name,
        artist=artist,
        duration_ms=duration_ms,
    )


def test_build_messages_includes_user_text_and_candidates():
    pb = PromptBuilder()
    tracks = [_track("sid1111111111111111111"), _track("sid2222222222222222222")]
    msgs = pb.build_messages("I want jazz", tracks, None)
    assert msgs[0]["role"] == "system"
    assert "JSON" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert "I want jazz" in msgs[1]["content"]
    assert "sid1111111111111111111" in msgs[1]["content"]
    assert "sid2222222222222222222" in msgs[1]["content"]


def test_build_messages_appends_feedback():
    pb = PromptBuilder()
    msgs = pb.build_messages("test", [_track("sid1111111111111111111")], "Fix your IDs.")
    assert "Fix your IDs." in msgs[1]["content"]


def test_respects_max_candidates(monkeypatch):
    from src.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "playlist_generation_max_candidates", 2)
    pb = PromptBuilder(settings=settings)
    a = "a" * 22
    b = "b" * 22
    c = "c" * 22
    tracks = [_track(a), _track(b), _track(c)]
    body = pb.build_messages("x", tracks, None)[1]["content"]
    assert a in body
    assert b in body
    assert c not in body
