from types import SimpleNamespace

import pytest

from app.routing import intent_router
from app.routing.models import Intent, CurrentMode


def test_prosody_intensity_numeric_and_strings():
    assert intent_router._prosody_intensity({"intensity": 0.4}) == 0.4
    assert intent_router._prosody_intensity({"intensity": "high"}) == 0.9
    assert intent_router._prosody_intensity({"intensity": "medium"}) == 0.5
    assert intent_router._prosody_intensity({"intensity": "low"}) == 0.1
    assert intent_router._prosody_intensity({"intensity": "unknown"}) == 0.0


@pytest.mark.asyncio
async def test_classify_intent_uses_prosody_bias(monkeypatch):
    async def fake_tier0(text, prosody=None):
        return SimpleNamespace(type=None, emotion="neutral", confidence=0.6)

    monkeypatch.setattr(intent_router, "classify_tier0_fast", fake_tier0)
    monkeypatch.setattr(intent_router, "track_intent", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(intent_router, "track_mode", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        intent_router, "track_utility_path", lambda *_args, **_kwargs: None
    )

    result = await intent_router.classify_intent_and_mode(
        "maybe", session_id="s", prosody={"intensity": "high"}
    )
    assert result.intent == Intent.UTILITY
    assert result.current_mode in (
        CurrentMode.UTILITY_DIRECT,
        CurrentMode.UTILITY_LIGHT,
        CurrentMode.UTILITY_AGENTIC,
    )
    assert result.utility_path is not None


@pytest.mark.asyncio
async def test_classify_intent_routes_utility_with_tier0_knowledge(monkeypatch):
    async def fake_tier0(text, prosody=None):
        return SimpleNamespace(
            type=intent_router.INTENT_KNOWLEDGE, emotion="neutral", confidence=0.8
        )

    monkeypatch.setattr(intent_router, "classify_tier0_fast", fake_tier0)
    monkeypatch.setattr(intent_router, "track_intent", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(intent_router, "track_mode", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        intent_router, "track_utility_path", lambda *_args, **_kwargs: None
    )

    result = await intent_router.classify_intent_and_mode(
        "explain quantum tunneling", session_id="s", prosody=None
    )
    assert result.intent == Intent.UTILITY
    assert result.current_mode in (
        CurrentMode.UTILITY_DIRECT,
        CurrentMode.UTILITY_LIGHT,
        CurrentMode.UTILITY_AGENTIC,
    )
    assert result.utility_path is not None


def test_utility_router_handles_context_heavy_short_question():
    result = intent_router.classify_utility_path("plan my vacation step by step")
    assert result.path.name.lower() == "light"
