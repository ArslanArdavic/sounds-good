"""Unit tests for duration inference and tolerance."""
import uuid
from types import SimpleNamespace

from src.services.duration_matcher import (
    duration_feedback,
    duration_within_tolerance,
    infer_target_duration_ms,
    total_duration_ms,
)


def test_infer_default_minutes(settings):
    ms = infer_target_duration_ms("something vague without numbers", settings)
    assert ms == settings.default_target_duration_minutes * 60 * 1000


def test_infer_hours():
    from src.config import get_settings

    ms = infer_target_duration_ms("about 2 hours of techno", get_settings())
    assert ms == 2 * 60 * 60 * 1000


def test_infer_minutes():
    from src.config import get_settings

    ms = infer_target_duration_ms("90 minutes long", get_settings())
    assert ms == 90 * 60 * 1000


def test_total_duration_ms():
    tracks = [
        SimpleNamespace(duration_ms=60_000),
        SimpleNamespace(duration_ms=30_000),
    ]
    assert total_duration_ms(tracks) == 90_000


def test_within_tolerance(settings):
    target = 45 * 60 * 1000
    assert duration_within_tolerance(target, target, settings)
    assert duration_within_tolerance(
        target + (settings.duration_tolerance_minutes * 60 * 1000),
        target,
        settings,
    )


def test_duration_feedback_text(settings):
    s = duration_feedback(30 * 60 * 1000, 45 * 60 * 1000, settings)
    assert "30" in s or "minutes" in s.lower()
