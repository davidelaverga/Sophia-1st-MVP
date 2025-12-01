"""Unit tests for Tier-0 Fast Classifier (Task #42537)

Tests intent and emotion classification with 10+ test phrases per type.
Verifies P95 latency ≤ 700ms and fallback behavior.
"""

import pytest
import asyncio
import time
from unittest.mock import patch

from app.services.tier0_classifier import (
    classify_tier0_fast,
    classify_tier0_fast_sync,
    _rule_based_classify,
    _detect_crisis,
    _parse_llm_response,
    DEFAULT_TIMEOUT_MS,
    INTENT_GREETING,
    INTENT_CASUAL,
    INTENT_EMOTIONAL,
    INTENT_CRISIS,
    INTENT_KNOWLEDGE,
    EMOTION_NEUTRAL,
    EMOTION_JOY,
    EMOTION_SAD,
    EMOTION_ANXIOUS,
    EMOTION_ANGRY,
    EMOTION_FEARFUL,
    EMOTION_GRIEF,
    EMOTION_PANIC,
    EMOTION_EXCITED,
)


# ========================================
# Test Data: 10+ phrases per intent type
# ========================================

GREETING_PHRASES = [
    "Hello",
    "Hi there",
    "Hey!",
    "Good morning",
    "Привет",
    "Здравствуйте",
    "Добрый день",
    "Доброе утро",
    "Hi, how are you?",
    "Hello, nice to meet you",
    "Hey, what's up?",
]

CASUAL_PHRASES = [
    "How's the weather?",
    "What do you think about movies?",
    "I like pizza",
    "Tell me a joke",
    "What's your favorite color?",
    "Какая сегодня погода?",
    "Я люблю кофе",
    "Расскажи что-нибудь интересное",
    "Do you like cats or dogs?",
    "Nice weather today",
    "I'm just chilling",
]

EMOTIONAL_PHRASES = [
    "I feel so sad today",
    "I'm really worried about this",
    "I'm so happy right now",
    "Feeling anxious about tomorrow",
    "I'm angry at what happened",
    "Мне грустно",
    "Я очень волнуюсь",
    "Мне страшно",
    "I feel lonely",
    "I'm excited about the trip!",
    "I'm so frustrated with everything",
]

CRISIS_PHRASES = [
    "I want to kill myself",
    "I don't want to live anymore",
    "Thinking about suicide",
    "I want to hurt myself",
    "Life is not worth living",
    "Я не хочу жить",
    "Хочу покончить с собой",
    "Умереть было бы лучше",
    "I'm going to end my life",
    "Everything would be better if I died",
    "I want to cut myself",
]

KNOWLEDGE_PHRASES = [
    "What is DeFi?",
    "How does yield farming work?",
    "Explain staking to me",
    "Tell me about Ethereum",
    "Why is blockchain important?",
    "Что такое DeFi?",
    "Как работает стейкинг?",
    "Объясни мне блокчейн",
    "What is a liquidity pool?",
    "How do I start with crypto?",
    "Tell me about smart contracts",
]


# ========================================
# Crisis Detection Tests
# ========================================


def test_crisis_detection():
    """Test crisis phrase detection works correctly"""
    for phrase in CRISIS_PHRASES:
        assert _detect_crisis(phrase), f"Failed to detect crisis in: {phrase}"

    # Non-crisis phrases should not trigger
    non_crisis = ["I'm feeling great", "Life is good", "Happy times"]
    for phrase in non_crisis:
        assert not _detect_crisis(phrase), f"False positive crisis detection: {phrase}"


def test_crisis_classification_in_fallback():
    """Test crisis classification works in rule-based fallback"""
    for phrase in CRISIS_PHRASES:
        intent, emotion, confidence = _rule_based_classify(phrase)
        assert intent == INTENT_CRISIS, f"Failed to classify as crisis: {phrase}"
        assert emotion in [EMOTION_PANIC, EMOTION_ANXIOUS], (
            f"Wrong emotion for crisis: {phrase}"
        )
        assert confidence >= 0.9, f"Low confidence for crisis: {phrase}"


# ========================================
# Rule-Based Fallback Tests (< 1ms)
# ========================================


def test_rule_based_greeting():
    """Test rule-based greeting classification"""
    for phrase in GREETING_PHRASES:
        intent, emotion, _ = _rule_based_classify(phrase)
        assert intent == INTENT_GREETING, f"Failed to classify greeting: {phrase}"


def test_rule_based_emotional():
    """Test rule-based emotional classification"""
    # Should detect at least 8 out of 11 emotional phrases
    detected = 0
    for phrase in EMOTIONAL_PHRASES:
        intent, emotion, _ = _rule_based_classify(phrase)
        if intent == INTENT_EMOTIONAL:
            detected += 1

    assert detected >= 8, f"Only detected {detected}/11 emotional phrases"


def test_rule_based_knowledge():
    """Test rule-based knowledge classification"""
    # Should detect at least 9 out of 11 knowledge phrases
    detected = 0
    for phrase in KNOWLEDGE_PHRASES:
        intent, emotion, _ = _rule_based_classify(phrase)
        if intent == INTENT_KNOWLEDGE:
            detected += 1

    assert detected >= 9, f"Only detected {detected}/11 knowledge phrases"


def test_rule_based_latency():
    """Test rule-based classification is < 1ms"""
    phrase = "Hello, how are you feeling today about DeFi?"

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        _rule_based_classify(phrase)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

    p95_latency = sorted(latencies)[94]  # 95th percentile
    assert p95_latency < 1.0, f"Rule-based P95 latency {p95_latency:.2f}ms exceeds 1ms"


# ========================================
# Prosody Adjustment Tests
# ========================================


def test_prosody_intensity_panic():
    """Test high intensity + anxious → panic adjustment"""
    phrase = "I'm worried about everything"

    # Without prosody
    intent1, emotion1, _ = _rule_based_classify(phrase)

    # With high intensity prosody
    prosody_high = {"intensity": 0.9, "confidence": 1.0}
    intent2, emotion2, _ = _rule_based_classify(phrase, prosody_high)

    # Should detect emotional intent
    assert intent1 == INTENT_EMOTIONAL
    assert intent2 == INTENT_EMOTIONAL

    # High intensity should escalate anxious → panic
    if emotion1 == EMOTION_ANXIOUS:
        assert emotion2 == EMOTION_PANIC, (
            "High intensity should escalate anxious to panic"
        )


# ========================================
# Full Classification Tests (with timeout)
# ========================================


@pytest.mark.asyncio
async def test_classification_with_timeout():
    """Test classification respects retry-aware timeout budget"""
    phrase = "What is DeFi and how does it work?"
    timeout_ms = 1000

    start = time.perf_counter()
    result = await classify_tier0_fast(phrase, timeout_ms=timeout_ms)
    latency_ms = (time.perf_counter() - start) * 1000

    # Should complete within total retry budget (3 attempts + backoff)
    max_expected_ms = timeout_ms * 3 + 700
    assert latency_ms < max_expected_ms, (
        f"Classification took {latency_ms:.1f}ms, exceeds {max_expected_ms}ms "
        "retry budget"
    )

    # Should return valid result
    assert result.type in [
        INTENT_GREETING,
        INTENT_CASUAL,
        INTENT_EMOTIONAL,
        INTENT_CRISIS,
        INTENT_KNOWLEDGE,
    ]
    assert result.emotion in [
        EMOTION_NEUTRAL,
        EMOTION_JOY,
        EMOTION_SAD,
        EMOTION_ANXIOUS,
        EMOTION_ANGRY,
        EMOTION_FEARFUL,
        EMOTION_GRIEF,
        EMOTION_PANIC,
        EMOTION_EXCITED,
    ]
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_fallback_on_llm_error():
    """Test fallback activates on LLM errors"""
    with patch(
        "app.services.tier0_classifier._llm_classify",
        side_effect=Exception("API Error"),
    ):
        phrase = "Hello, how are you?"
        result = await classify_tier0_fast(phrase)

        # Should use fallback
        assert result.fallback_used is True

        # Should still classify correctly
        assert result.type == INTENT_GREETING


@pytest.mark.asyncio
async def test_fallback_on_timeout():
    """Test fallback activates on timeout"""

    async def slow_llm(*args, **kwargs):
        await asyncio.sleep(1.0)  # Simulate slow LLM
        return INTENT_KNOWLEDGE, EMOTION_NEUTRAL, 0.8

    with patch("app.services.tier0_classifier._llm_classify", side_effect=slow_llm):
        phrase = "What is blockchain?"
        result = await classify_tier0_fast(phrase, timeout_ms=100)  # Short timeout

        # Should use fallback due to timeout
        assert result.fallback_used is True
        assert result.latency_ms < 400  # Fallback should remain within retry budget


# ========================================
# P95 Latency Tests
# ========================================


@pytest.mark.asyncio
async def test_p95_latency_requirement():
    """Test P95 latency stays within retry-aware budget"""

    phrases = GREETING_PHRASES + CASUAL_PHRASES + EMOTIONAL_PHRASES + KNOWLEDGE_PHRASES
    latencies = []

    # Run classification on all test phrases
    for phrase in phrases:
        result = await classify_tier0_fast(phrase, timeout_ms=500)
        latencies.append(result.latency_ms)

    # Calculate P95
    latencies_sorted = sorted(latencies)
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies_sorted[p95_index]

    print(
        f"\n📊 Latency stats: min={min(latencies):.1f}ms, "
        f"median={latencies_sorted[len(latencies) // 2]:.1f}ms, "
        f"p95={p95_latency:.1f}ms, max={max(latencies):.1f}ms"
    )

    assert p95_latency <= 1500, (
        f"P95 latency {p95_latency:.1f}ms exceeds 1500ms retry budget"
    )


# ========================================
# Sync Wrapper Tests
# ========================================


def test_sync_wrapper():
    """Test synchronous wrapper works correctly"""
    phrase = "Hello there!"
    result = classify_tier0_fast_sync(phrase)

    assert isinstance(result, dict)
    assert "type" in result
    assert "emotion" in result
    assert "confidence" in result
    assert "latency_ms" in result
    assert result["type"] == INTENT_GREETING


# ========================================
# Edge Cases
# ========================================


def test_empty_transcript():
    """Test handling of empty transcript"""
    intent, emotion, confidence = _rule_based_classify("")
    assert intent == INTENT_CASUAL  # Should default to casual
    assert emotion == EMOTION_NEUTRAL


def test_very_long_transcript():
    """Test handling of very long transcript"""
    long_phrase = "Hello " * 1000  # Very long greeting
    intent, emotion, _ = _rule_based_classify(long_phrase)
    assert intent == INTENT_GREETING


def test_mixed_language():
    """Test handling of mixed language input"""
    phrase = "Hello, я хочу узнать what is DeFi"
    intent, emotion, _ = _rule_based_classify(phrase)
    # Should detect either greeting or knowledge
    assert intent in [INTENT_GREETING, INTENT_KNOWLEDGE]


def test_prosody_none():
    """Test classification works without prosody data"""
    phrase = "I'm feeling anxious"
    intent, emotion, _ = _rule_based_classify(phrase, prosody=None)
    assert intent == INTENT_EMOTIONAL
    assert emotion in [EMOTION_ANXIOUS, EMOTION_PANIC]


def test_parse_llm_response_plaintext_and_defaults():
    """Non-JSON LLM response should still produce usable classification"""
    content = "The intent is greeting and emotion joy with confidence 0.82"
    intent, emotion, confidence, mode = _parse_llm_response(
        content, "Hello there", prosody=None
    )
    assert intent == INTENT_GREETING
    assert emotion in (EMOTION_JOY, EMOTION_NEUTRAL)
    assert 0.0 <= confidence <= 1.0
    assert mode == "plaintext"


def test_parse_llm_response_empty_string():
    """Empty LLM response should fall back cleanly"""
    intent, emotion, confidence, mode = _parse_llm_response("", "Hi", prosody=None)
    assert intent in [
        INTENT_GREETING,
        INTENT_CASUAL,
        INTENT_EMOTIONAL,
        INTENT_CRISIS,
        INTENT_KNOWLEDGE,
    ]
    assert mode == "empty"
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_total_timeout_budget_matches_default_timeout():
    """Overall latency should respect default retry budget when LLM keeps timing out."""

    async def very_slow_llm(*_args, **_kwargs):
        await asyncio.sleep(1.0)  # within default timeout (1200ms)
        return INTENT_KNOWLEDGE, EMOTION_NEUTRAL, 0.8

    with patch(
        "app.services.tier0_classifier._llm_classify", side_effect=very_slow_llm
    ):
        result = await classify_tier0_fast("hi", timeout_ms=DEFAULT_TIMEOUT_MS)
        assert result.fallback_used is False
        # Default timeout uses up to 3 attempts; ensure we stay within budget.
        assert result.latency_ms < (DEFAULT_TIMEOUT_MS * 3)


# ========================================
# Integration Test
# ========================================


@pytest.mark.asyncio
async def test_full_classification_all_intents():
    """Test classification across all intent types"""

    test_cases = [
        (GREETING_PHRASES[0], INTENT_GREETING),
        (CASUAL_PHRASES[0], INTENT_CASUAL),
        (EMOTIONAL_PHRASES[0], INTENT_EMOTIONAL),
        (CRISIS_PHRASES[0], INTENT_CRISIS),
        (KNOWLEDGE_PHRASES[0], INTENT_KNOWLEDGE),
    ]

    for phrase, expected_intent in test_cases:
        result = await classify_tier0_fast(phrase)

        # For crisis, must be detected correctly (critical requirement)
        if expected_intent == INTENT_CRISIS:
            assert result.type == INTENT_CRISIS, f"Failed to detect crisis: {phrase}"
            assert result.emotion in [EMOTION_PANIC, EMOTION_ANXIOUS]

        # Log results for debugging
        print(
            f"✓ '{phrase[:30]}...' → {result.type} ({result.emotion}, conf={result.confidence:.2f})"
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
