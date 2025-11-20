import pytest

from app.routing.models import UtilityPath
from app.routing.utility_router import classify_utility_path


def _assert_valid_result(result):
    assert 0.0 <= result.confidence <= 1.0
    assert result.reasoning


def test_reflection_cue_routes_agentic():
    result = classify_utility_path("Can you turn this into a reflection card?")
    _assert_valid_result(result)
    assert result.path == UtilityPath.AGENTIC
    assert result.confidence >= 0.85
    assert "reflection" in result.reasoning.lower()


@pytest.mark.parametrize(
    "message",
    [
        "hi",
        "bye",
        "thank you",
        "what time is it?",
        "weather today?",
    ],
)
def test_trivial_or_short_factoid_routes_direct(message):
    result = classify_utility_path(message)
    _assert_valid_result(result)
    assert result.path == UtilityPath.DIRECT
    assert result.confidence >= 0.7


def test_context_heavy_short_routes_light():
    result = classify_utility_path("help me write a cover letter")
    _assert_valid_result(result)
    assert result.path == UtilityPath.LIGHT
    assert "light" in result.reasoning.lower()


def test_default_to_light_when_not_short_or_reflection():
    message = (
        "Explain the process of getting a mortgage step by step for first-time buyers."
    )
    result = classify_utility_path(message)
    _assert_valid_result(result)
    assert result.path == UtilityPath.LIGHT
