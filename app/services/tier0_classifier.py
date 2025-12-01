"""Tier-0 Fast Classifier with Mistral Small and Rule-Based Fallback.

Targets sub-second intent and emotion classification with resilient parsing.
Falls back to rule-based patterns if LLM fails or times out.
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from mistralai import Mistral
except ImportError:  # pragma: no cover - optional dependency for fast path
    Mistral = None
from app.config import get_settings
from prometheus_client import Counter, Gauge

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

# Prometheus metrics
tier0_timeout_count = Counter(
    "tier0_timeout_count", "Number of tier-0 LLM classification timeouts"
)
tier0_json_error_count = Counter(
    "tier0_json_error_count", "Number of tier-0 LLM JSON parsing failures"
)
tier0_success_rate_percent = Gauge(
    "tier0_success_rate_percent",
    "Tier-0 LLM classification success rate (percentage)",
)
tier0_request_total = Counter(
    "tier0_request_total",
    "Total tier-0 classification outcomes",
    ["outcome"],  # success, fallback
)
# Pre-register outcomes to avoid missing label errors
for _outcome in ("success", "fallback"):
    tier0_request_total.labels(outcome=_outcome)

_tier0_success_total = 0
_tier0_total = 0


def _update_success_rate(success: bool) -> None:
    """Update moving success rate gauge safely."""
    global _tier0_success_total, _tier0_total
    _tier0_total += 1
    if success:
        _tier0_success_total += 1

    rate = (_tier0_success_total / _tier0_total) * 100 if _tier0_total else 0.0
    tier0_success_rate_percent.set(rate)


# Crisis keywords (self-harm, suicide)
CRISIS_PATTERNS = [
    r"\b(kill|suicide|die|death|end.*life|hurt.*myself|harm.*myself)\b",
    r"\b(don'?t\s+want\s+to\s+live|want\s+to\s+die|life.*not.*worth)\b",
    r"\b(не.*хоч.*жить|суицид|убить.*себ|покончить|умер)",
    r"\b(cut.*myself|overdose|jump.*off|hang.*myself)\b",
    r"\b(better.*if.*died|end.*it.*all|take.*my.*life)\b",
]

INTENT_LABELS = {
    INTENT_GREETING,
    INTENT_CASUAL,
    INTENT_EMOTIONAL,
    INTENT_CRISIS,
    INTENT_KNOWLEDGE,
}

EMOTION_LABELS = {
    EMOTION_NEUTRAL,
    EMOTION_JOY,
    EMOTION_SAD,
    EMOTION_ANXIOUS,
    EMOTION_ANGRY,
    EMOTION_FEARFUL,
    EMOTION_GRIEF,
    EMOTION_PANIC,
    EMOTION_EXCITED,
}

INTENT_ALIASES = {
    "hello": INTENT_GREETING,
    "greet": INTENT_GREETING,
    "hi": INTENT_GREETING,
    "casual": INTENT_CASUAL,
    "chitchat": INTENT_CASUAL,
    "small talk": INTENT_CASUAL,
    "emotional_sharing": INTENT_EMOTIONAL,
    "emotional": INTENT_EMOTIONAL,
    "feelings": INTENT_EMOTIONAL,
    "crisis": INTENT_CRISIS,
    "urgent": INTENT_CRISIS,
    "self-harm": INTENT_CRISIS,
    "knowledge": INTENT_KNOWLEDGE,
    "question": INTENT_KNOWLEDGE,
}

EMOTION_ALIASES = {
    "neutral": EMOTION_NEUTRAL,
    "joy": EMOTION_JOY,
    "happy": EMOTION_JOY,
    "happiness": EMOTION_JOY,
    "sad": EMOTION_SAD,
    "anxious": EMOTION_ANXIOUS,
    "anxiety": EMOTION_ANXIOUS,
    "angry": EMOTION_ANGRY,
    "anger": EMOTION_ANGRY,
    "fearful": EMOTION_FEARFUL,
    "fear": EMOTION_FEARFUL,
    "grief": EMOTION_GRIEF,
    "panic": EMOTION_PANIC,
    "excited": EMOTION_EXCITED,
}

DEFAULT_INTENT = INTENT_CASUAL
DEFAULT_EMOTION = EMOTION_NEUTRAL
DEFAULT_CONFIDENCE = 0.5
DEFAULT_TIMEOUT_MS = 1200


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
    if Mistral is None:
        raise RuntimeError("mistralai SDK is not installed")
    settings = get_settings()
    if not settings.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    return Mistral(api_key=settings.MISTRAL_API_KEY)


def _parse_json_from_content(raw: str) -> Dict[str, Any]:
    """Extract a JSON object from an LLM chat completion string.

    Handles common cases like:
    - Bare JSON: '{"intent": "...", ...}'
    - JSON wrapped in ``` or ```json fences
    - JSON with surrounding whitespace or commentary (we take the first {...} block).

    Raises ValueError if no JSON object can be located or parsed.
    """

    if raw is None:
        raise ValueError("Empty response from Mistral API")

    text = raw.strip()
    if not text:
        raise ValueError("Empty response from Mistral API")

    # Strip Markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            # Drop first (``` or ```json) and last (```)
            inner = "\n".join(lines[1:-1]).strip()
            if inner:
                text = inner

    # Take substring spanning the outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"Could not locate JSON object in Mistral response: {text[:80]!r}"
        )

    json_str = text[start : end + 1]
    return json.loads(json_str)


def _detect_crisis(text: str) -> bool:
    """Detect crisis/self-harm phrases in text (rule-based, always fast)"""
    text_lower = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"🚨 CRISIS DETECTED in text: '{text[:50]}...'")
            return True
    return False


def _rule_based_classify(
    transcript: str, prosody: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, float]:
    """Rule-based intent and emotion classification (< 1ms fallback).

    Returns: (intent, emotion, confidence)
    """
    text_lower = transcript.lower().strip()

    # 1. Crisis detection (highest priority)
    if _detect_crisis(transcript):
        emotion = (
            EMOTION_PANIC
            if prosody and prosody.get("intensity", 0) > 0.7
            else EMOTION_ANXIOUS
        )
        return INTENT_CRISIS, emotion, 0.95

    # 2. Detect emotions first (before intent detection)
    emotion_keywords = {
        EMOTION_SAD: [
            "sad",
            "depressed",
            "down",
            "upset",
            "unhappy",
            "lonely",
            "miserable",
            "blue",
            "heartbroken",
            "feeling sad",
            "feel sad",
            "i'm sad",
            "грустн",
            "печал",
            "тоск",
            "одинок",
        ],
        EMOTION_ANXIOUS: [
            "worried",
            "anxious",
            "stressed",
            "nervous",
            "concerned",
            "uneasy",
            "tense",
            "overwhelmed",
            "feeling anxious",
            "feel worried",
            "i'm worried",
            "тревож",
            "беспоко",
            "волну",
        ],
        EMOTION_ANGRY: [
            "angry",
            "mad",
            "furious",
            "annoyed",
            "frustrated",
            "irritated",
            "pissed",
            "enraged",
            "feeling angry",
            "feel angry",
            "i'm angry",
            "злой",
            "раздраж",
            "бесит",
        ],
        EMOTION_FEARFUL: [
            "scared",
            "afraid",
            "terrified",
            "frightened",
            "fearful",
            "panicked",
            "feeling scared",
            "feel afraid",
            "i'm scared",
            "страшн",
            "боюсь",
        ],
        EMOTION_JOY: [
            "happy",
            "joyful",
            "glad",
            "cheerful",
            "delighted",
            "pleased",
            "excited",
            "thrilled",
            "feeling happy",
            "feel happy",
            "i'm happy",
            "радост",
            "счастлив",
            "весел",
        ],
        EMOTION_EXCITED: [
            "excited",
            "thrilled",
            "pumped",
            "energized",
            "enthusiastic",
            "eager",
            "feeling excited",
            "feel excited",
            "i'm excited",
            "взволнован",
            "воодушевл",
        ],
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
    # 3a. Greeting detection (English + Russian variants)
    greeting_patterns = [
        r"\b(hi|hello|hey|yo|sup|greetings)\b",
        r"\b(good\s+(?:morning|afternoon|evening|day))\b",
        r"\b(привет|здраст[вуйте]*|здравств[уйте]*)\b",
        r"\b(доброе?\s+утро|добры[йе]\s+день|добры[йе]\s+вечер|доброй\s+ночи)\b",
    ]
    greeting_terms = [
        "доброе утро",
        "добрый день",
        "добрый вечер",
        "доброй ночи",
    ]
    is_greeting = any(
        re.search(pattern, text_lower) for pattern in greeting_patterns
    ) or any(term in text_lower for term in greeting_terms)

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
        "what",
        "how",
        "why",
        "explain",
        "tell",
        "defi",
        "yield",
        "staking",
        "стейкинг",
        "token",
        "tokenomics",
        "blockchain",
        "блокчейн",
        "ethereum",
        "liquidity",
        "liquidity pool",
        "smart contract",
        "смарт контракт",
        "crypto",
        "крипт",
        "что",
        "как",
        "почему",
        "объясни",
        "расскажи",
    ]
    if any(kw in text_lower for kw in knowledge_keywords):
        return INTENT_KNOWLEDGE, EMOTION_NEUTRAL, 0.70

    # 5. Default: casual conversation
    return INTENT_CASUAL, EMOTION_NEUTRAL, 0.60


def _clamp_confidence(value: Any) -> float:
    """Convert confidence to a bounded float."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = DEFAULT_CONFIDENCE
    return max(0.0, min(confidence, 1.0))


def _canonical_intent(intent: Optional[str]) -> str:
    """Normalize intent labels and fall back to defaults."""
    if not intent:
        return DEFAULT_INTENT
    value = str(intent).lower().strip()
    if value in INTENT_LABELS:
        return value
    for alias, canonical in INTENT_ALIASES.items():
        if alias in value:
            return canonical
    return DEFAULT_INTENT


def _canonical_emotion(emotion: Optional[str]) -> str:
    """Normalize emotion labels and fall back to defaults."""
    if not emotion:
        return DEFAULT_EMOTION
    value = str(emotion).lower().strip()
    if value in EMOTION_LABELS:
        return value
    for alias, canonical in EMOTION_ALIASES.items():
        if alias in value:
            return canonical
    return DEFAULT_EMOTION


def _parse_confidence_from_text(text: str) -> Optional[float]:
    """Extract confidence value from free-form text."""
    match = re.search(r"confidence[^0-9]*([01](?:\.\d+)?|0?\.\d+)", text)
    if match:
        return float(match.group(1))
    return None


def _parse_plain_text_response(
    content: str, transcript: str, prosody: Optional[Dict[str, Any]]
) -> Tuple[str, str, float, str]:
    """Handle non-JSON responses like 'intent is greeting, emotion joy'."""
    content_lower = content.lower()
    intent = None
    emotion = None

    for alias, canonical in INTENT_ALIASES.items():
        if alias in content_lower:
            intent = canonical
            break

    for alias, canonical in EMOTION_ALIASES.items():
        if alias in content_lower:
            emotion = canonical
            break

    confidence_val = _parse_confidence_from_text(content_lower)

    if intent is None or emotion is None:
        fallback_intent, fallback_emotion, fallback_conf = _rule_based_classify(
            transcript, prosody
        )
        intent = intent or fallback_intent
        emotion = emotion or fallback_emotion
        confidence = (
            _clamp_confidence(confidence_val)
            if confidence_val is not None
            else max(fallback_conf, DEFAULT_CONFIDENCE)
        )
    else:
        confidence = _clamp_confidence(
            confidence_val if confidence_val is not None else DEFAULT_CONFIDENCE
        )

    return intent, emotion, confidence, "plaintext"


def _parse_llm_response(
    content: str, transcript: str, prosody: Optional[Dict[str, Any]]
) -> Tuple[str, str, float, str]:
    """Parse LLM content into structured labels with resilient fallbacks."""
    if not content or not content.strip():
        tier0_json_error_count.inc()
        logger.warning("Tier-0: Empty response from Mistral API")
        intent, emotion, confidence = _rule_based_classify(transcript, prosody)
        return intent, emotion, confidence, "empty"

    trimmed = content.strip()

    # Try to isolate the JSON object if extra text is present
    candidate = trimmed
    if "{" in trimmed and "}" in trimmed:
        candidate = trimmed[trimmed.find("{") : trimmed.rfind("}") + 1]

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as err:
        tier0_json_error_count.inc()
        logger.warning("Tier-0: JSON parse failed (%s). Raw content='%s'", err, trimmed)
        return _parse_plain_text_response(trimmed, transcript, prosody)

    if isinstance(payload, str):
        return _parse_plain_text_response(payload, transcript, prosody)

    if not isinstance(payload, dict):
        tier0_json_error_count.inc()
        logger.warning(
            "Tier-0: Unexpected payload type %s. Raw content='%s'",
            type(payload),
            trimmed,
        )
        return _parse_plain_text_response(trimmed, transcript, prosody)

    intent_raw = payload.get("intent")
    emotion_raw = payload.get("emotion")
    confidence_raw = payload.get("confidence", DEFAULT_CONFIDENCE)

    missing_fields = [
        field
        for field, raw in (("intent", intent_raw), ("emotion", emotion_raw))
        if raw in (None, "")
    ]
    if missing_fields:
        tier0_json_error_count.inc()
        logger.warning(
            "Tier-0: Missing fields %s in LLM response, applying defaults. Raw='%s'",
            missing_fields,
            trimmed,
        )

    intent = _canonical_intent(intent_raw)
    emotion = _canonical_emotion(emotion_raw)
    confidence = _clamp_confidence(confidence_raw)
    return intent, emotion, confidence, "json"


def _build_prompt(transcript: str) -> str:
    """Compact prompt with constrained output and few-shot hints."""
    user_text = transcript.replace('"', '\\"').strip()
    return (
        "Classify the user message fast. "
        'Return ONLY JSON: {"intent":"...","emotion":"...","confidence":0.0-1.0}. '
        "Intents: greeting, casual, emotional_sharing, crisis, knowledge. "
        "Emotions: neutral, joy, sad, anxious, angry, fearful, grief, panic, excited. "
        'Example: "Hi there!" -> {"intent":"greeting","emotion":"joy","confidence":0.85}. '
        'Example: "I want to hurt myself" -> {"intent":"crisis","emotion":"panic","confidence":0.95}. '
        f'User: "{user_text}"'
    )


def _normalize_llm_result(result: Tuple[Any, ...]) -> Tuple[str, str, float, str, str]:
    """Support both legacy 3-field and new 5-field LLM outputs."""
    intent = DEFAULT_INTENT
    emotion = DEFAULT_EMOTION
    confidence = DEFAULT_CONFIDENCE
    parse_mode = "stub"
    raw_content = ""

    if isinstance(result, (list, tuple)):
        if len(result) >= 3:
            intent = _canonical_intent(result[0])
            emotion = _canonical_emotion(result[1])
            confidence = _clamp_confidence(result[2])
        if len(result) >= 4:
            parse_mode = str(result[3])
        if len(result) >= 5:
            raw_content = str(result[4])

    return intent, emotion, confidence, parse_mode, raw_content


async def _llm_classify(
    transcript: str, prosody: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, float, str, str]:
    """LLM-based classification using Mistral Small with robust parsing."""
    prompt = _build_prompt(transcript)
    client = _get_mistral_client()

    def _invoke() -> str:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=40,
        )
        return response.choices[0].message.content or ""

    raw_content = await asyncio.to_thread(_invoke)
    logger.debug("Tier-0 raw LLM response: %s", raw_content)

    intent, emotion, confidence, parse_mode = _parse_llm_response(
        raw_content, transcript, prosody
    )

    return intent, emotion, confidence, parse_mode, raw_content


async def classify_tier0_fast(
    transcript: str,
    prosody: Optional[Dict[str, Any]] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ClassificationResult:
    """Fast tier-0 classification with retries and graceful fallbacks.

    Args:
        transcript: User speech transcript
        prosody: Optional prosody features dict with keys:
                 - intensity: 0-1 (voice intensity)
                 - pitch: Hz (voice pitch)
                 - confidence: 0-1 (ASR confidence)
        timeout_ms: Per-attempt timeout for LLM classification (default 1000ms)

    Returns:
        ClassificationResult with intent, emotion, confidence, and metadata
    """

    start_time = time.perf_counter()
    fallback_used = False
    last_error: Optional[Exception] = None
    parse_mode = "json"
    raw_content = ""

    # Use fewer retries when per-attempt timeout is small to avoid long fallbacks
    max_retries = (
        1 if timeout_ms <= 600 else 2
    )  # default 2 attempts at 1200ms ≈ 2.4s budget
    backoff_base = 0.05  # seconds
    total_budget_ms = timeout_ms * (max_retries + 1)

    # Extract prosody features
    asr_confidence = prosody.get("confidence", 1.0) if prosody else 1.0
    voice_signal_present = prosody.get("voice_detected", True) if prosody else True

    intent = DEFAULT_INTENT
    emotion = DEFAULT_EMOTION
    confidence = DEFAULT_CONFIDENCE

    llm_result: Optional[Tuple[str, str, float, str, str]] = None

    for attempt in range(max_retries + 1):
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        remaining_ms = total_budget_ms - elapsed_ms
        if remaining_ms <= 0:
            logger.warning(
                "Tier-0: Total budget exhausted before attempt %s", attempt + 1
            )
            break

        attempt_timeout_ms = min(timeout_ms, int(remaining_ms))
        try:
            logger.info(
                "Tier-0: LLM attempt %s/%s (timeout=%sms, remaining=%.0fms)",
                attempt + 1,
                max_retries + 1,
                attempt_timeout_ms,
                remaining_ms,
            )
            llm_result = await asyncio.wait_for(
                _llm_classify(transcript, prosody),
                timeout=attempt_timeout_ms / 1000.0,
            )
            break
        except asyncio.TimeoutError as err:
            tier0_timeout_count.inc()
            last_error = err
            logger.warning(
                "Tier-0: LLM attempt %s timed out after %sms",
                attempt + 1,
                attempt_timeout_ms,
            )
        except Exception as err:  # noqa: BLE001 - we need to catch-and-fallback
            last_error = err
            logger.warning("Tier-0: LLM attempt %s failed: %s", attempt + 1, err)
            # Configuration errors are not retryable
            if isinstance(err, RuntimeError):
                break

        if attempt < max_retries:
            backoff = min(backoff_base * (2**attempt), remaining_ms / 1000.0)
            if backoff > 0:
                await asyncio.sleep(backoff)

    if llm_result is not None:
        intent, emotion, confidence, parse_mode, raw_content = _normalize_llm_result(
            llm_result
        )
        # Adjust emotion based on prosody
        if prosody and prosody.get("intensity", 0) > 0.8 and emotion == EMOTION_ANXIOUS:
            emotion = EMOTION_PANIC
            logger.info(
                "Tier-0: Adjusted emotion anxious → panic (high prosody intensity)"
            )
    else:
        fallback_used = True
        intent, emotion, confidence = _rule_based_classify(transcript, prosody)

    latency_ms = (time.perf_counter() - start_time) * 1000

    if not fallback_used:
        logger.info(
            "Tier-0 LLM classification completed via %s: intent=%s, emotion=%s, "
            "confidence=%.2f, latency=%.1fms",
            parse_mode,
            intent,
            emotion,
            confidence,
            latency_ms,
        )
        if raw_content:
            logger.debug("Tier-0 LLM raw content: %s", raw_content)
    else:
        reason = last_error or "no LLM result"
        logger.warning(
            "Tier-0: Using rule-based fallback after LLM failure (%s). Latency=%.1fms",
            reason,
            latency_ms,
        )

    # Double-check for crisis in fallback mode (safety net)
    if fallback_used and _detect_crisis(transcript):
        intent = INTENT_CRISIS
        emotion = (
            EMOTION_PANIC
            if prosody and prosody.get("intensity", 0) > 0.7
            else EMOTION_ANXIOUS
        )
        confidence = 0.95
        logger.warning("Tier-0: Crisis detected in fallback mode")

    # Metrics
    metrics_success = not fallback_used
    outcome = "success" if metrics_success else "fallback"
    tier0_request_total.labels(outcome=outcome).inc()
    _update_success_rate(metrics_success)

    return ClassificationResult(
        type=intent,
        emotion=emotion,
        confidence=confidence,
        asr_confidence=asr_confidence,
        voice_signal_present=voice_signal_present,
        latency_ms=latency_ms,
        fallback_used=fallback_used,
        source="rule_based_fallback" if fallback_used else "mistral_llm",
    )


# Synchronous wrapper for compatibility
def classify_tier0_fast_sync(
    transcript: str,
    prosody: Optional[Dict[str, Any]] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> Dict[str, Any]:
    """Synchronous wrapper for classify_tier0_fast().

    Returns dict with keys: type, emotion, confidence, asr_confidence,
                            voice_signal_present, latency_ms, fallback_used
    """
    coro = classify_tier0_fast(transcript, prosody, timeout_ms)
    try:
        result = asyncio.run(coro)
    except RuntimeError as err:
        if "asyncio.run()" not in str(err):
            raise
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    return {
        "type": result.type,
        "emotion": result.emotion,
        "confidence": result.confidence,
        "asr_confidence": result.asr_confidence,
        "voice_signal_present": result.voice_signal_present,
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback_used,
    }
