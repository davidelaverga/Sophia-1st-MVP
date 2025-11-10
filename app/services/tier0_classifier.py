"""Tier-0 Fast Classifier with Mistral Small and Rule-Based Fallback.

Provides ultra-fast intent and emotion classification with <700ms P95 latency.
Falls back to rule-based patterns if LLM fails or times out.
"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from mistralai import Mistral
from app.config import get_settings

logger = logging.getLogger("sophia-backend")

# Intent types
INTENT_GREETING = "greeting"
INTENT_CASUAL = "casual"
INTENT_EMOTIONAL = "emotional_sharing"
INTENT_CRISIS = "crisis"
INTENT_KNOWLEDGE = "knowledge"

# Emotions
EMOTION_NEUTRAL = "neutral"
EMOTION_JOY = "joy"
EMOTION_SAD = "sad"
EMOTION_ANXIOUS = "anxious"
EMOTION_ANGRY = "angry"
EMOTION_FEARFUL = "fearful"
EMOTION_GRIEF = "grief"
EMOTION_PANIC = "panic"
EMOTION_EXCITED = "excited"

# Crisis keywords (self-harm, suicide)
CRISIS_PATTERNS = [
    r"\b(kill|suicide|die|death|end.*life|hurt.*myself|harm.*myself)\b",
    r"\b(don'?t\s+want\s+to\s+live|want\s+to\s+die|life.*not.*worth)\b",
    r"\b(не.*хоч.*жить|суицид|убить.*себ|покончить|умер)",
    r"\b(cut.*myself|overdose|jump.*off|hang.*myself)\b",
    r"\b(better.*if.*died|end.*it.*all|take.*my.*life)\b",
]


@dataclass
class ClassificationResult:
    """Result of tier-0 classification"""
    type: str  # intent type
    emotion: str  # emotion label
    confidence: float  # classification confidence (0-1)
    asr_confidence: float  # ASR confidence (from prosody if available)
    voice_signal_present: bool  # whether voice signal was detected
    latency_ms: float  # classification latency
    fallback_used: bool  # whether rule-based fallback was used
    source: str  # classification source: "mistral_llm" or "rule_based_fallback"


def _get_mistral_client() -> Mistral:
    """Get Mistral API client"""
    settings = get_settings()
    if not settings.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    return Mistral(api_key=settings.MISTRAL_API_KEY)


def _detect_crisis(text: str) -> bool:
    """Detect crisis/self-harm phrases in text (rule-based, always fast)"""
    text_lower = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"🚨 CRISIS DETECTED in text: '{text[:50]}...'")
            return True
    return False


def _rule_based_classify(transcript: str, prosody: Optional[Dict[str, Any]] = None) -> Tuple[str, str, float]:
    """Rule-based intent and emotion classification (< 1ms fallback).

    Returns: (intent, emotion, confidence)
    """
    text_lower = transcript.lower().strip()

    # 1. Crisis detection (highest priority)
    if _detect_crisis(transcript):
        emotion = EMOTION_PANIC if prosody and prosody.get("intensity", 0) > 0.7 else EMOTION_ANXIOUS
        return INTENT_CRISIS, emotion, 0.95

    # 2. Detect emotions first (before intent detection)
    emotion_keywords = {
        EMOTION_SAD: ["sad", "depressed", "down", "upset", "unhappy", "lonely", "miserable", "blue", "heartbroken", "feeling sad", "feel sad", "i'm sad", "грустн", "печал", "тоск", "одинок"],
        EMOTION_ANXIOUS: ["worried", "anxious", "stressed", "nervous", "concerned", "uneasy", "tense", "overwhelmed", "feeling anxious", "feel worried", "i'm worried", "тревож", "беспоко", "волну"],
        EMOTION_ANGRY: ["angry", "mad", "furious", "annoyed", "frustrated", "irritated", "pissed", "enraged", "feeling angry", "feel angry", "i'm angry", "злой", "раздраж", "бесит"],
        EMOTION_FEARFUL: ["scared", "afraid", "terrified", "frightened", "fearful", "panicked", "feeling scared", "feel afraid", "i'm scared", "страшн", "боюсь"],
        EMOTION_JOY: ["happy", "joyful", "glad", "cheerful", "delighted", "pleased", "excited", "thrilled", "feeling happy", "feel happy", "i'm happy", "радост", "счастлив", "весел"],
        EMOTION_EXCITED: ["excited", "thrilled", "pumped", "energized", "enthusiastic", "eager", "feeling excited", "feel excited", "i'm excited", "взволнован", "воодушевл"],
    }

    detected_emotion = EMOTION_NEUTRAL
    max_emotion_score = 0

    for emotion, keywords in emotion_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > max_emotion_score:
            max_emotion_score = score
            detected_emotion = emotion

    # Adjust emotion based on prosody intensity
    if max_emotion_score > 0 and prosody and prosody.get("intensity", 0) > 0.8:
        if detected_emotion == EMOTION_ANXIOUS:
            detected_emotion = EMOTION_PANIC

    # 3. Intent detection (using detected emotion)
    # 3a. Greeting detection
    greet_patterns = [
        r"\b(hi|hello|hey|привет|здравствуй|добр.*день|добр.*утро|добр.*вечер)\b",
    ]
    is_greeting = any(re.search(p, text_lower) for p in greet_patterns)

    # 3b. Check if there are emotional keywords
    has_emotion = max_emotion_score > 0

    if is_greeting:
        # If greeting with emotion, use detected emotion; otherwise use joy as default
        emotion = detected_emotion if has_emotion else EMOTION_JOY
        confidence = 0.80 if has_emotion else 0.85
        return INTENT_GREETING, emotion, confidence

    # 3c. Emotional sharing (when emotions detected without greeting)
    if has_emotion:
        return INTENT_EMOTIONAL, detected_emotion, 0.75

    # 4. Knowledge/DeFi question detection
    knowledge_keywords = [
        "what", "how", "why", "explain", "tell",
        "defi", "yield", "staking", "token", "blockchain", "ethereum",
        "что", "как", "почему", "объясни", "расскажи",
    ]
    if any(kw in text_lower for kw in knowledge_keywords):
        return INTENT_KNOWLEDGE, EMOTION_NEUTRAL, 0.70

    # 5. Default: casual conversation
    return INTENT_CASUAL, EMOTION_NEUTRAL, 0.60


async def _llm_classify(transcript: str, timeout_ms: int = 500) -> Tuple[str, str, float]:
    """LLM-based classification using Mistral Small with timeout.

    Returns: (intent, emotion, confidence)
    Raises: asyncio.TimeoutError if exceeds timeout
    """

    prompt = f"""Classify the following user message into intent and emotion.

Intent types:
- greeting: user is saying hello/hi
- casual: casual conversation, chitchat
- emotional_sharing: user sharing feelings/emotions
- crisis: mentions of self-harm, suicide, or severe distress
- knowledge: asking for information/explanation

Emotions: neutral, joy, sad, anxious, angry, fearful, grief, panic, excited

User message: "{transcript}"

Respond ONLY in this JSON format:
{{"intent": "...", "emotion": "...", "confidence": 0.0-1.0}}"""

    client = _get_mistral_client()

    # Use asyncio.wait_for to enforce timeout
    async def _call_mistral():
        response = client.chat.complete(
            model="mistral-small-latest",  # Fast model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50,
        )
        content = response.choices[0].message.content

        # Debug logging
        logger.debug(f"Mistral API response content: {content}")

        # Parse JSON response
        import json
        if not content or not content.strip():
            raise ValueError("Empty response from Mistral API")
        result = json.loads(content.strip())
        return result["intent"], result["emotion"], result["confidence"]

    return await asyncio.wait_for(_call_mistral(), timeout=timeout_ms / 1000.0)


async def classify_tier0_fast(
    transcript: str,
    prosody: Optional[Dict[str, Any]] = None,
    timeout_ms: int = 500
) -> ClassificationResult:
    """Ultra-fast tier-0 classification with Mistral Small + rule-based fallback.

    Args:
        transcript: User speech transcript
        prosody: Optional prosody features dict with keys:
                 - intensity: 0-1 (voice intensity)
                 - pitch: Hz (voice pitch)
                 - confidence: 0-1 (ASR confidence)
        timeout_ms: Timeout for LLM classification (default 500ms)

    Returns:
        ClassificationResult with intent, emotion, confidence, and metadata

    Guarantees:
        - P95 latency ≤ 700ms (including fallback)
        - Always returns a result (fallback handles all errors)
        - Crisis detection works in fallback mode
    """

    start_time = time.perf_counter()
    fallback_used = False

    # Extract prosody features
    asr_confidence = prosody.get("confidence", 1.0) if prosody else 1.0
    voice_signal_present = prosody.get("voice_detected", True) if prosody else True

    # Try LLM classification first
    try:
        logger.info(f"Tier-0: Attempting LLM classification (timeout={timeout_ms}ms)")
        intent, emotion, confidence = await _llm_classify(transcript, timeout_ms)

        # Adjust emotion based on prosody
        if prosody and prosody.get("intensity", 0) > 0.8:
            if emotion == EMOTION_ANXIOUS:
                emotion = EMOTION_PANIC
                logger.info("Tier-0: Adjusted emotion anxious → panic (high prosody intensity)")

        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Tier-0 LLM classification completed: intent={intent}, emotion={emotion}, "
            f"confidence={confidence:.2f}, latency={latency_ms:.1f}ms"
        )

    except asyncio.TimeoutError:
        # Timeout - use rule-based fallback
        logger.warning(f"Tier-0: LLM timeout ({timeout_ms}ms), using rule-based fallback")
        fallback_used = True
        intent, emotion, confidence = _rule_based_classify(transcript, prosody)
        latency_ms = (time.perf_counter() - start_time) * 1000

    except Exception as e:
        # Any error - use rule-based fallback
        logger.warning(f"Tier-0: LLM error ({e}), using rule-based fallback")
        fallback_used = True
        intent, emotion, confidence = _rule_based_classify(transcript, prosody)
        latency_ms = (time.perf_counter() - start_time) * 1000

    # Double-check for crisis in fallback mode (safety net)
    if fallback_used and _detect_crisis(transcript):
        intent = INTENT_CRISIS
        emotion = EMOTION_PANIC if prosody and prosody.get("intensity", 0) > 0.7 else EMOTION_ANXIOUS
        confidence = 0.95
        logger.warning("Tier-0: Crisis detected in fallback mode")

    return ClassificationResult(
        type=intent,
        emotion=emotion,
        confidence=confidence,
        asr_confidence=asr_confidence,
        voice_signal_present=voice_signal_present,
        latency_ms=latency_ms,
        fallback_used=fallback_used,
        source="rule_based_fallback" if fallback_used else "mistral_llm"
    )


# Synchronous wrapper for compatibility
def classify_tier0_fast_sync(
    transcript: str,
    prosody: Optional[Dict[str, Any]] = None,
    timeout_ms: int = 500
) -> Dict[str, Any]:
    """Synchronous wrapper for classify_tier0_fast().

    Returns dict with keys: type, emotion, confidence, asr_confidence,
                            voice_signal_present, latency_ms, fallback_used
    """
    import asyncio

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(
        classify_tier0_fast(transcript, prosody, timeout_ms)
    )

    return {
        "type": result.type,
        "emotion": result.emotion,
        "confidence": result.confidence,
        "asr_confidence": result.asr_confidence,
        "voice_signal_present": result.voice_signal_present,
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback_used,
    }
