import pytest

from app.routing.emotional_router import (
    ConversationMeta,
    EmotionalSkill,
    route_emotional_skill,
)


def test_crisis_redirect_overrides_everything():
    meta = ConversationMeta(conversation_count=7)
    result = route_emotional_skill("I want to die tonight", meta)

    assert result.skill == EmotionalSkill.CRISIS_REDIRECT
    assert result.confidence == pytest.approx(0.99)
    assert "Crisis markers detected" in result.reasoning


def test_boundary_holding_triggers_without_gating():
    meta = ConversationMeta(conversation_count=1)
    result = route_emotional_skill("Can you send nudes?", meta)

    assert result.skill == EmotionalSkill.BOUNDARY_HOLDING
    assert result.confidence == pytest.approx(0.95)
    assert "Boundary markers detected" in result.reasoning


def test_breakthrough_requires_conversation_count_gate():
    early_meta = ConversationMeta(conversation_count=1)
    early_result = route_emotional_skill(
        "It just clicked, a huge breakthrough for me", early_meta
    )
    assert early_result.skill == EmotionalSkill.TRUST_BUILDING
    assert "conversation_count=1" in early_result.reasoning

    allowed_meta = ConversationMeta(conversation_count=4)
    allowed_result = route_emotional_skill(
        "It just clicked, a huge breakthrough for me", allowed_meta
    )
    assert allowed_result.skill == EmotionalSkill.CELEBRATING_BREAKTHROUGH
    assert "conversation_count=4" in allowed_result.reasoning


def test_growth_requires_deep_trust():
    blocked_meta = ConversationMeta(conversation_count=5)
    blocked_result = route_emotional_skill(
        "push me and challenge me hard", blocked_meta
    )
    assert blocked_result.skill == EmotionalSkill.ACTIVE_LISTENING
    assert "conversation_count=5" in blocked_result.reasoning

    allowed_meta = ConversationMeta(conversation_count=12)
    allowed_result = route_emotional_skill(
        "push me and challenge me hard", allowed_meta
    )
    assert allowed_result.skill == EmotionalSkill.CHALLENGING_GROWTH
    assert "conversation_count=12" in allowed_result.reasoning


def test_identity_fluidity_support_selected():
    meta = ConversationMeta(conversation_count=6)
    result = route_emotional_skill("As a queer woman I'm exploring who I am", meta)

    assert result.skill == EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT
    assert "Identity cues" in result.reasoning


def test_trust_building_bias_for_early_turns():
    meta = ConversationMeta(conversation_count=2)
    result = route_emotional_skill(
        "It's my first time here and I'm seeing if I can open up.", meta
    )

    assert result.skill == EmotionalSkill.TRUST_BUILDING
    assert "trust-building cues" in result.reasoning.lower()


def test_vulnerability_holding_when_emotion_shared():
    meta = ConversationMeta(conversation_count=5)
    result = route_emotional_skill("I'm feeling anxious and lonely tonight", meta)

    assert result.skill == EmotionalSkill.VULNERABILITY_HOLDING
    assert "Vulnerability cues" in result.reasoning


def test_fallback_to_active_listening_when_unclear():
    meta = ConversationMeta(conversation_count=8)
    result = route_emotional_skill("Just thinking out loud", meta)

    assert result.skill == EmotionalSkill.ACTIVE_LISTENING
    assert "defaulting to ACTIVE_LISTENING" in result.reasoning


_BULK_CASES = [
    ("I want to die", 5, EmotionalSkill.CRISIS_REDIRECT),
    ("I'm on the bridge with a rope", 1, EmotionalSkill.CRISIS_REDIRECT),
    ("I have a plan to end it tonight", 7, EmotionalSkill.CRISIS_REDIRECT),
    ("You're stupid", 3, EmotionalSkill.BOUNDARY_HOLDING),
    ("send nudes", 10, EmotionalSkill.BOUNDARY_HOLDING),
    ("what's your limit", 2, EmotionalSkill.BOUNDARY_HOLDING),
    ("fuck you", 9, EmotionalSkill.BOUNDARY_HOLDING),
    (
        "It just clicked, massive breakthrough",
        3,
        EmotionalSkill.CELEBRATING_BREAKTHROUGH,
    ),
    ("aha moment it just clicked", 7, EmotionalSkill.CELEBRATING_BREAKTHROUGH),
    (
        "never saw it this way, what an epiphany",
        6,
        EmotionalSkill.CELEBRATING_BREAKTHROUGH,
    ),
    ("breakthrough landed but we're early", 2, EmotionalSkill.TRUST_BUILDING),
    ("push me hard, I need tough love", 10, EmotionalSkill.CHALLENGING_GROWTH),
    ("call me out on my pattern", 15, EmotionalSkill.CHALLENGING_GROWTH),
    ("challenge me to improve", 5, EmotionalSkill.ACTIVE_LISTENING),
    ("growth is slow but challenge me gently", 2, EmotionalSkill.TRUST_BUILDING),
    ("help me change, stuck in a pattern", 12, EmotionalSkill.CHALLENGING_GROWTH),
    ("who am I really", 5, EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT),
    (
        "as a queer immigrant I'm figuring things out",
        8,
        EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT,
    ),
    ("I don't know who I am anymore", 11, EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT),
    ("I am trans and uncertain", 4, EmotionalSkill.IDENTITY_FLUIDITY_SUPPORT),
    ("first time here, can I be honest?", 1, EmotionalSkill.TRUST_BUILDING),
    ("are you safe to open up to?", 3, EmotionalSkill.TRUST_BUILDING),
    ("trust is new for me here", 6, EmotionalSkill.TRUST_BUILDING),
    ("I feel anxious and scared", 6, EmotionalSkill.VULNERABILITY_HOLDING),
    ("I'm sad and lonely", 3, EmotionalSkill.VULNERABILITY_HOLDING),
    ("My chest hurts from all this pain", 9, EmotionalSkill.VULNERABILITY_HOLDING),
    ("It's hard to trust people", 2, EmotionalSkill.TRUST_BUILDING),
    ("hello there", 2, EmotionalSkill.TRUST_BUILDING),
    ("just checking in", 1, EmotionalSkill.TRUST_BUILDING),
    ("thinking about dinner plans", 5, EmotionalSkill.ACTIVE_LISTENING),
    ("random note to self", 8, EmotionalSkill.ACTIVE_LISTENING),
    ("I can't take it anymore, I want to end it", 3, EmotionalSkill.CRISIS_REDIRECT),
    ("on the roof with a rope", 4, EmotionalSkill.CRISIS_REDIRECT),
]

assert len(_BULK_CASES) >= 30, "Need at least 30 bulk routing cases for coverage."


@pytest.mark.parametrize("message,conv_count,expected", _BULK_CASES)
def test_bulk_routing_over_30_inputs(message, conv_count, expected):
    meta = ConversationMeta(conversation_count=conv_count)
    result = route_emotional_skill(message, meta)

    assert result.skill == expected, (
        f"{message!r} (count={conv_count}) routed to {result.skill}"
    )
