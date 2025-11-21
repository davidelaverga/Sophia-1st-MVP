import pytest
from types import SimpleNamespace

from app.routing import intent_router
from app.routing.models import CurrentMode, Intent, UtilityPath


@pytest.mark.asyncio
async def test_intent_router_accuracy_with_stubbed_tier0(monkeypatch):
    """Ensure intent routing hits >=90% accuracy on emotional vs utility classification."""

    # Stub tier-0 to avoid external calls and keep deterministic scoring.
    async def fake_tier0(text: str, prosody=None):
        text_lower = text.lower()
        if intent_router._has_pattern(text_lower, tuple(intent_router.EMOTIONAL_HINTS)):
            intent_type = intent_router.INTENT_EMOTIONAL
        elif intent_router._has_pattern(text_lower, tuple(intent_router.UTILITY_HINTS)):
            intent_type = intent_router.INTENT_KNOWLEDGE
        else:
            intent_type = intent_router.INTENT_CASUAL
        return SimpleNamespace(type=intent_type, emotion="neutral", confidence=0.8)

    monkeypatch.setattr(intent_router, "classify_tier0_fast", fake_tier0)

    cases = [
        ("I feel overwhelmed and sad today.", Intent.EMOTIONAL_SUPPORT),
        ("I'm anxious about the exam.", Intent.EMOTIONAL_SUPPORT),
        ("I'm scared of flying tomorrow.", Intent.EMOTIONAL_SUPPORT),
        ("I'm lost and don't know what to do.", Intent.EMOTIONAL_SUPPORT),
        ("I feel like crying all day.", Intent.EMOTIONAL_SUPPORT),
        ("I'm afraid I'll disappoint my family.", Intent.EMOTIONAL_SUPPORT),
        ("I feel stuck and lonely.", Intent.EMOTIONAL_SUPPORT),
        ("I'm sad because my dog is sick.", Intent.EMOTIONAL_SUPPORT),
        ("I'm anxious and can't sleep.", Intent.EMOTIONAL_SUPPORT),
        ("I feel nervous about my new job.", Intent.EMOTIONAL_SUPPORT),
        ("Explain the theory of relativity in simple terms.", Intent.UTILITY),
        ("Summarize the key points of this article.", Intent.UTILITY),
        ("How do I update my resume step by step?", Intent.UTILITY),
        ("Help me write an apology email.", Intent.UTILITY),
        ("Step by step, how do I change a flat tire?", Intent.UTILITY),
        ("Can you explain how to use Git branches?", Intent.UTILITY),
        ("Summarize the meeting notes from today.", Intent.UTILITY),
        ("How do I cook pasta step by step?", Intent.UTILITY),
        ("Help me write a thank-you note.", Intent.UTILITY),
        ("Explain basic budgeting in simple language.", Intent.UTILITY),
        ("How do I back up my phone?", Intent.UTILITY),
        ("I feel so tense and anxious right now.", Intent.EMOTIONAL_SUPPORT),
    ]

    correct = 0
    for message, expected_intent in cases:
        result = await intent_router.classify_intent_and_mode(
            user_message=message, session_id="test-session"
        )
        if result.intent == expected_intent:
            correct += 1

        # Additional sanity checks on modes for each branch.
        if expected_intent == Intent.EMOTIONAL_SUPPORT:
            assert result.current_mode == CurrentMode.EMOTIONAL_SUPPORT
            assert result.utility_path is None
        else:
            assert result.utility_path is not None
            assert result.current_mode in {
                CurrentMode.UTILITY_LIGHT,
                CurrentMode.UTILITY_DIRECT,
                CurrentMode.UTILITY_AGENTIC,
            }
            # Mode should mirror the chosen utility path.
            if result.utility_path == UtilityPath.DIRECT:
                assert result.current_mode == CurrentMode.UTILITY_DIRECT
            elif result.utility_path == UtilityPath.LIGHT:
                assert result.current_mode == CurrentMode.UTILITY_LIGHT
            elif result.utility_path == UtilityPath.AGENTIC:
                assert result.current_mode == CurrentMode.UTILITY_AGENTIC

    accuracy = correct / len(cases)
    assert accuracy >= 0.90, f"Intent accuracy below expectation: {accuracy:.2%}"
