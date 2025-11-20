"""Tests for helper utilities."""

import time
from pathlib import Path

import pytest

from app.helpers import prosody_features


DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        ("low.pcm", "low"),
        ("medium.pcm", "medium"),
        ("high.pcm", "high"),
    ],
)
def test_prosody_features_intensity_levels(fixture_name, expected):
    payload = (DATA_DIR / fixture_name).read_bytes()
    start = time.perf_counter()
    result = prosody_features(payload)
    duration_ms = (time.perf_counter() - start) * 1000
    assert result == {"intensity": expected}
    assert duration_ms < 5, f"prosody_features took {duration_ms:.3f} ms"


def test_prosody_features_invalid_bytes_defaults_low():
    assert prosody_features(b"") == {"intensity": "low"}
