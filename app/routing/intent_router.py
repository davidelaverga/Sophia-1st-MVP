import logging
import re
from typing import Any, Dict, Optional, Tuple

from app.routing.models import (
    CurrentMode,
    Intent,
    IntentResult,
    UtilityPath,
    UtilityPathResult,
)
from app.routing.utility_router import classify_utility_path
from app.services.tier0_classifier import (
    INTENT_CASUAL,
    INTENT_CRISIS,
    INTENT_EMOTIONAL,
    INTENT_GREETING,
    INTENT_KNOWLEDGE,
    classify_tier0_fast,
)
from app.obs.metrics import track_intent, track_mode, track_utility_path

logger = logging.getLogger("sophia-backend")

# Explicit substring cues (client-provided phrases only)
EMOTIONAL_HINTS = [
    r"\bi feel\b",
    r"\bi'm scared\b",
    r"\bi'm afraid\b",
    r"\bi'm sad\b",
    r"\bi'm lost\b",
    r"\bi'm anxious\b",
]

UTILITY_HINTS = [
    r"\bexplain\b",
    r"\bsummarize\b",
    r"\bhow do i\b",
    r"\bhelp me write\b",
    r"\bstep by step\b",
]


def _has_pattern(text: str, patterns: Tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _prosody_intensity(prosody: Dict[str, float]) -> float:
    """Normalize prosody intensity to a float scale."""
    raw = prosody.get("intensity")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        level = raw.lower()
        if level == "high":
            return 0.9
        if level == "medium":
            return 0.5
        if level == "low":
            return 0.1
    return 0.0


async def classify_intent_and_mode(
    user_message: str, session_id: str, tier0_result: Optional[Dict[str, Any]] = None, prosody: Optional[Dict[str, float]] = None
) -> IntentResult:
    """
    Primary routing entrypoint.

    - Uses tier-0 classifier for coarse intent.
    - Applies lightweight hint checks for emotional vs utility.
    - Biases ambiguous messages toward emotional support.
    """

    text = (user_message or "").strip()
    text_lower = text.lower()
    reason_chunks = []

    tier0_intent = None
    tier0_confidence = 0.6

    try:
        tier0_emotion = None
        if tier0_result is None:
            tier0 = await classify_tier0_fast(text, prosody=prosody)
            tier0_intent = tier0.type
            tier0_confidence = tier0.confidence
            tier0_emotion = tier0.emotion
        else:
            tier0_intent = tier0_result.get('intent', tier0_intent)
            tier0_confidence = tier0_result.get('confidence', tier0_confidence)
            tier0_emotion = tier0_result.get('emotion', tier0_emotion)
        reason_chunks.append(
            f"Tier-0 intent={tier0_intent}, emotion={tier0_emotion}, conf={tier0_confidence:.2f}."
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Tier-0 classifier failed, continuing with heuristics: %s", exc)
        reason_chunks.append("Tier-0 unavailable, using heuristic routing.")

    emotional_score = 0.0
    utility_score = 0.0

    if tier0_intent in (INTENT_EMOTIONAL, INTENT_CRISIS):
        emotional_score += 2.5
        reason_chunks.append("Tier-0 marked message as emotional/crisis.")
    elif tier0_intent == INTENT_KNOWLEDGE:
        utility_score += 2.5
        reason_chunks.append("Tier-0 marked message as knowledge/utility.")
    elif tier0_intent in (INTENT_GREETING, INTENT_CASUAL):
        emotional_score += 0.6
        reason_chunks.append("Tier-0 saw casual/greeting tone.")

    if _has_pattern(text_lower, tuple(EMOTIONAL_HINTS)):
        emotional_score += 1.5
        reason_chunks.append('Emotional hint detected ("I feel"/"scared").')

    if _has_pattern(text_lower, tuple(UTILITY_HINTS)):
        utility_score += 1.5
        reason_chunks.append("Utility hint detected (explain/summarize/how-to).")

    if "?" in text_lower or _has_pattern(
        text_lower, (r"\bwhat\b", r"\bhow\b", r"\bwhy\b")
    ):
        utility_score += 0.4
        reason_chunks.append("Interrogative phrasing nudges toward utility.")

    if prosody:
        intensity_score = _prosody_intensity(prosody)
        if intensity_score > 0.7:
            emotional_score += 0.2
            reason_chunks.append("Elevated prosody intensity nudges toward emotional.")

    chosen_intent = (
        Intent.UTILITY if utility_score > emotional_score else Intent.EMOTIONAL_SUPPORT
    )

    if abs(utility_score - emotional_score) < 0.25:
        chosen_intent = Intent.UTILITY
        reason_chunks.append("Ambiguous intent; biasing toward utility.")

    confidence_gap = abs(utility_score - emotional_score)
    base_conf = max(0.55, tier0_confidence)
    final_confidence = min(0.99, base_conf + 0.1 * confidence_gap)

    if chosen_intent == Intent.EMOTIONAL_SUPPORT:
        reasoning = " ".join(reason_chunks)

        # Track metrics
        track_intent(Intent.EMOTIONAL_SUPPORT.value)
        track_mode(CurrentMode.EMOTIONAL_SUPPORT.value)

        return IntentResult(
            intent=Intent.EMOTIONAL_SUPPORT,
            current_mode=CurrentMode.EMOTIONAL_SUPPORT,
            utility_path=None,
            confidence=final_confidence,
            reasoning=reasoning,
        )

    utility_path_result: UtilityPathResult = classify_utility_path(text)
    utility_path = utility_path_result.path
    if utility_path == UtilityPath.DIRECT:
        current_mode = CurrentMode.UTILITY_DIRECT
    elif utility_path == UtilityPath.LIGHT:
        current_mode = CurrentMode.UTILITY_LIGHT
    else:
        current_mode = CurrentMode.UTILITY_AGENTIC

    reasoning = " ".join(reason_chunks + [utility_path_result.reasoning])
    combined_confidence = max(final_confidence, utility_path_result.confidence)

    # Track metrics
    track_intent(Intent.UTILITY.value)
    track_mode(current_mode.value)
    track_utility_path(utility_path.value)

    return IntentResult(
        intent=Intent.UTILITY,
        current_mode=current_mode,
        utility_path=utility_path,
        confidence=combined_confidence,
        reasoning=reasoning,
    )
