"""Routing logic for Sophia's emotional intelligence skills.

This router applies a strict priority order across safety, boundaries, and
growth-oriented skills. It uses lightweight marker checks plus Tier-0 style
labels (provided or heuristically inferred) and lightly biases toward trust
building for very early relationships.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from app.routing.markers import MarkerMatch, match_markers

logger = logging.getLogger("sophia-backend")


class EmotionalSkill(str, Enum):
    CRISIS_REDIRECT = "CRISIS_REDIRECT"
    BOUNDARY_HOLDING = "BOUNDARY_HOLDING"
    CELEBRATING_BREAKTHROUGH = "CELEBRATING_BREAKTHROUGH"
    CHALLENGING_GROWTH = "CHALLENGING_GROWTH"
    IDENTITY_FLUIDITY_SUPPORT = "IDENTITY_FLUIDITY_SUPPORT"
    TRUST_BUILDING = "TRUST_BUILDING"
    VULNERABILITY_HOLDING = "VULNERABILITY_HOLDING"
    ACTIVE_LISTENING = "ACTIVE_LISTENING"


@dataclass
class ConversationMeta:
    conversation_count: int
    last_skill: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class EmotionalRoutingResult:
    skill: EmotionalSkill
    confidence: float
    reasoning: str
    tier0_label: Optional[str] = None
    markers: Optional[MarkerMatch] = None


_LABEL_PATTERNS: dict[str, Sequence[re.Pattern[str]]] = {
    "breakthrough": (
        re.compile(r"\bbreakthrough\b", re.IGNORECASE),
        re.compile(r"\baha\b", re.IGNORECASE),
        re.compile(r"\bepiphany\b", re.IGNORECASE),
        re.compile(r"\b(it )?just clicked\b", re.IGNORECASE),
        re.compile(r"\bfinally (see|saw|get)\b", re.IGNORECASE),
        re.compile(r"\bnever saw it (that|this) way\b", re.IGNORECASE),
    ),
    "growth": (
        re.compile(r"\bchallenge me\b", re.IGNORECASE),
        re.compile(r"\bpush me\b", re.IGNORECASE),
        re.compile(r"\bhold me accountable\b", re.IGNORECASE),
        re.compile(r"\bcall me out\b", re.IGNORECASE),
        re.compile(r"\bgrowth\b", re.IGNORECASE),
        re.compile(r"\bstuck in (a )?pattern", re.IGNORECASE),
        re.compile(r"\bhelp me change\b", re.IGNORECASE),
        re.compile(r"\btough love\b", re.IGNORECASE),
    ),
    "identity": (
        re.compile(r"\bidentity\b", re.IGNORECASE),
        re.compile(r"\bwho am i\b", re.IGNORECASE),
        re.compile(r"\bdon't know who i am\b", re.IGNORECASE),
        re.compile(r"\bas a [a-z]{2,}\b", re.IGNORECASE),
        re.compile(
            r"\bi am (trans|queer|gay|bi|non[- ]?binary|immigrant|woman|man)\b",
            re.IGNORECASE,
        ),
    ),
    "trust": (
        re.compile(r"\btrust\b", re.IGNORECASE),
        re.compile(r"\bfirst time\b", re.IGNORECASE),
        re.compile(r"\bnew here\b", re.IGNORECASE),
        re.compile(r"\bcan i be honest\b", re.IGNORECASE),
        re.compile(r"\bare you (safe|real)\b", re.IGNORECASE),
        re.compile(r"\bnot sure i can open up\b", re.IGNORECASE),
    ),
    "vulnerability": (
        re.compile(r"\bi feel\b", re.IGNORECASE),
        re.compile(r"\bi[' ]?m feeling\b", re.IGNORECASE),
        re.compile(r"\banxious\b", re.IGNORECASE),
        re.compile(r"\bsad\b", re.IGNORECASE),
        re.compile(r"\bscared\b", re.IGNORECASE),
        re.compile(r"\bafraid\b", re.IGNORECASE),
        re.compile(r"\bhurt\b", re.IGNORECASE),
        re.compile(r"\blonely\b", re.IGNORECASE),
        re.compile(r"\bstressed\b", re.IGNORECASE),
        re.compile(r"\boverwhelmed\b", re.IGNORECASE),
        re.compile(r"\bpain\b", re.IGNORECASE),
    ),
}

_SKILL_CONFIDENCE = {
    EmotionalSkill.CRISIS_REDIRECT: 0.99,
    EmotionalSkill.BOUNDARY_HOLDING: 0.95,
    EmotionalSkill.CELEBRATING_BREAKTHROUGH: 0.9,
    EmotionalSkill.CHALLENGING_GROWTH: 0.88,
    EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT: 0.82,
    EmotionalSkill.TRUST_BUILDING: 0.78,
    EmotionalSkill.VULNERABILITY_HOLDING: 0.76,
    EmotionalSkill.ACTIVE_LISTENING: 0.5,
}


def _infer_label_from_text(
    text: str, provided_label: Optional[str]
) -> Tuple[Optional[str], float, List[str]]:
    """
    Lightweight Tier-0 style inference for emotional skill labels.

    Returns: (label, confidence, reasoning_chunks)
    """
    reasons: List[str] = []
    normalized_label = (provided_label or "").strip().lower() or None

    if normalized_label:
        reasons.append(f"Tier-0 label provided: {normalized_label}.")
        return normalized_label, 0.9, reasons

    normalized_text = text.lower().strip()
    if not normalized_text:
        reasons.append("Empty text; cannot infer label.")
        return None, 0.0, reasons

    best_label: Optional[str] = None
    best_score = 0
    best_patterns: List[str] = []

    for label, patterns in _LABEL_PATTERNS.items():
        hits = [p.pattern for p in patterns if p.search(normalized_text)]
        if not hits:
            continue
        score = len(hits)
        if score > best_score:
            best_score = score
            best_label = label
            best_patterns = hits

    if best_label:
        confidence = min(0.55 + 0.1 * best_score, 0.9)
        reasons.append(
            f"Inferred label '{best_label}' from cues: {', '.join(best_patterns)}."
        )
        return best_label, confidence, reasons

    reasons.append("No Tier-0 label inferred from text.")
    return None, 0.0, reasons


def _confidence_for(skill: EmotionalSkill, label_confidence: float) -> float:
    base = _SKILL_CONFIDENCE.get(skill, 0.7)
    return max(base, label_confidence or 0.0)


def _format_markers(markers: MarkerMatch) -> str:
    crisis = ", ".join(sorted(markers.crisis_markers)) if markers.crisis_markers else ""
    boundary = (
        ", ".join(sorted(markers.boundary_markers)) if markers.boundary_markers else ""
    )
    parts = []
    if crisis:
        parts.append(f"crisis=[{crisis}]")
    if boundary:
        parts.append(f"boundary=[{boundary}]")
    return "; ".join(parts)


def route_emotional_skill(
    user_message: str,
    meta: ConversationMeta,
    tier0_label: Optional[str] = None,
) -> EmotionalRoutingResult:
    """
    Route to an emotional skill using safety-first priority:

    1) Crisis markers      -> CRISIS_REDIRECT (0.99)
    2) Boundary markers    -> BOUNDARY_HOLDING (0.95)
    3) breakthrough label  -> CELEBRATING_BREAKTHROUGH if conversation_count >= 3
    4) growth label        -> CHALLENGING_GROWTH if conversation_count >= 10
    5) identity label      -> IDENTITY_FLUIDITY_SUPPORT
    6) trust label         -> TRUST_BUILDING
    7) vulnerability label -> VULNERABILITY_HOLDING
    8) Fallback            -> ACTIVE_LISTENING (0.5)
    """

    text = (user_message or "").strip()
    reasons: List[str] = []
    markers = match_markers(text)

    if markers.crisis_markers:
        marker_summary = _format_markers(markers)
        reasons.append(
            f"Crisis markers detected ({marker_summary}); overriding to CRISIS_REDIRECT."
        )
        return EmotionalRoutingResult(
            skill=EmotionalSkill.CRISIS_REDIRECT,
            confidence=_SKILL_CONFIDENCE[EmotionalSkill.CRISIS_REDIRECT],
            reasoning=" ".join(reasons),
            tier0_label=tier0_label or "crisis",
            markers=markers,
        )

    if markers.boundary_markers:
        marker_summary = _format_markers(markers)
        reasons.append(
            f"Boundary markers detected ({marker_summary}); using BOUNDARY_HOLDING."
        )
        return EmotionalRoutingResult(
            skill=EmotionalSkill.BOUNDARY_HOLDING,
            confidence=_SKILL_CONFIDENCE[EmotionalSkill.BOUNDARY_HOLDING],
            reasoning=" ".join(reasons),
            tier0_label=tier0_label or "boundary",
            markers=markers,
        )

    label, label_conf, label_reasons = _infer_label_from_text(text, tier0_label)
    reasons.extend(label_reasons)

    conversation_count = meta.conversation_count if meta else 0
    early_conversation = conversation_count <= 2

    if label == "breakthrough":
        if conversation_count >= 3:
            reasons.append(
                f"Tier-0 label 'breakthrough' with conversation_count={conversation_count} (>=3)."
            )
            return EmotionalRoutingResult(
                skill=EmotionalSkill.CELEBRATING_BREAKTHROUGH,
                confidence=_confidence_for(
                    EmotionalSkill.CELEBRATING_BREAKTHROUGH, label_conf
                ),
                reasoning=" ".join(reasons),
                tier0_label=label,
                markers=markers,
            )
        reasons.append(
            f"Breakthrough cues present but conversation_count={conversation_count} < 3; deferring."
        )

    if label == "growth":
        if conversation_count >= 10:
            reasons.append(
                f"Tier-0 label 'growth' and conversation_count={conversation_count} (>=10)."
            )
            return EmotionalRoutingResult(
                skill=EmotionalSkill.CHALLENGING_GROWTH,
                confidence=_confidence_for(
                    EmotionalSkill.CHALLENGING_GROWTH, label_conf
                ),
                reasoning=" ".join(reasons),
                tier0_label=label,
                markers=markers,
            )
        reasons.append(
            f"Growth cues present but conversation_count={conversation_count} < 10; deferring."
        )

    if label == "identity":
        reasons.append("Identity cues detected; routing to IDENTITY_FLUIDITY_SUPPORT.")
        return EmotionalRoutingResult(
            skill=EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT,
            confidence=_confidence_for(
                EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT, label_conf
            ),
            reasoning=" ".join(reasons),
            tier0_label=label,
            markers=markers,
        )

    if label == "trust":
        reasons.append("Trust-building cues detected; routing to TRUST_BUILDING.")
        return EmotionalRoutingResult(
            skill=EmotionalSkill.TRUST_BUILDING,
            confidence=_confidence_for(EmotionalSkill.TRUST_BUILDING, label_conf),
            reasoning=" ".join(reasons),
            tier0_label=label,
            markers=markers,
        )

    if label == "vulnerability":
        reasons.append("Vulnerability cues detected; routing to VULNERABILITY_HOLDING.")
        return EmotionalRoutingResult(
            skill=EmotionalSkill.VULNERABILITY_HOLDING,
            confidence=_confidence_for(
                EmotionalSkill.VULNERABILITY_HOLDING, label_conf
            ),
            reasoning=" ".join(reasons),
            tier0_label=label,
            markers=markers,
        )

    if early_conversation:
        reasons.append(
            f"Very early conversation (count={conversation_count}); favoring TRUST_BUILDING/ACTIVE_LISTENING."
        )
        return EmotionalRoutingResult(
            skill=EmotionalSkill.TRUST_BUILDING,
            confidence=_SKILL_CONFIDENCE[EmotionalSkill.TRUST_BUILDING],
            reasoning=" ".join(reasons),
            tier0_label=label,
            markers=markers,
        )

    reasons.append(
        "No decisive label; defaulting to ACTIVE_LISTENING baseline support."
    )
    return EmotionalRoutingResult(
        skill=EmotionalSkill.ACTIVE_LISTENING,
        confidence=_SKILL_CONFIDENCE[EmotionalSkill.ACTIVE_LISTENING],
        reasoning=" ".join(reasons),
        tier0_label=label,
        markers=markers,
    )
