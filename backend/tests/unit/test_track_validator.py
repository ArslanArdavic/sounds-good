"""Unit tests for track ID validation helpers."""
from src.services.track_validator import validate_track_ids


def test_validate_preserves_order_and_dedupes():
    allowed = {"a", "b", "c"}
    valid, invalid = validate_track_ids(["a", "b", "a", "x"], allowed)
    assert valid == ["a", "b"]
    assert invalid == ["x"]


def test_all_invalid():
    valid, invalid = validate_track_ids(["z"], {"a"})
    assert valid == []
    assert invalid == ["z"]


def test_splits_valid_and_invalid():
    valid, invalid = validate_track_ids(["a", "bad", "b"], {"a", "b", "c"})
    assert valid == ["a", "b"]
    assert invalid == ["bad"]
