from unittest.mock import patch

from app.graph.nodes.emotional_router import EmotionalSkillRouterNode
from app.routing.emotional_router import (
    EmotionalRoutingResult,
    EmotionalSkill,
    route_emotional_skill,
)
from app.routing.models import CurrentMode


def _router_returning(skill: EmotionalSkill):
    """Return a stub router that always yields the given skill."""

    def _stub(message, meta, tier0_label=None):
        return EmotionalRoutingResult(
            skill=skill,
            confidence=1.0,
            reasoning="stub",
            tier0_label=tier0_label,
            markers=None,
        )

    return _stub


def _base_state(**overrides):
    state = {
        "current_mode": CurrentMode.EMOTIONAL_SUPPORT,
        "conversation_count": 0,
        "last_skill": None,
        "user_id": "user-123",
        "transcript": "hi",
    }
    state.update(overrides)
    return state


def test_crisis_flag_set():
    node = EmotionalSkillRouterNode(
        router=_router_returning(EmotionalSkill.CRISIS_REDIRECT)
    )
    state = _base_state(had_crisis=False, had_boundary=False)

    result = node(state)

    assert result["had_crisis"] is True
    assert result["had_boundary"] is False
    assert result["skill_id"] == EmotionalSkill.CRISIS_REDIRECT.value


def test_boundary_flag_set_and_preserves_existing_crisis():
    node = EmotionalSkillRouterNode(
        router=_router_returning(EmotionalSkill.BOUNDARY_HOLDING)
    )
    state = _base_state(had_crisis=True, had_boundary=False)

    result = node(state)

    assert result["had_crisis"] is True  # remains true from prior crisis
    assert result["had_boundary"] is True
    assert result["skill_id"] == EmotionalSkill.BOUNDARY_HOLDING.value


def test_defaults_initialized_when_not_emotional_mode():
    node = EmotionalSkillRouterNode(
        router=_router_returning(EmotionalSkill.ACTIVE_LISTENING)
    )
    state = _base_state(current_mode=CurrentMode.UTILITY_LIGHT)
    state.pop("had_crisis", None)
    state.pop("had_boundary", None)

    result = node(state)

    assert result["had_crisis"] is False
    assert result["had_boundary"] is False


# ============================================================================
# TASK #42825: Skill Distribution Metrics & Tests
# ============================================================================


@patch("app.graph.nodes.emotional_router.track_crisis_override")
@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_crisis_override(mock_track_skill, mock_track_crisis):
    """Test that suicidal phrases trigger CRISIS_REDIRECT and metrics are tracked."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    # Test with suicidal phrase
    state = _base_state(
        transcript="I want to kill myself",
        conversation_count=5,
    )

    result = node(state)

    assert result["skill_id"] == EmotionalSkill.CRISIS_REDIRECT.value
    assert result["had_crisis"] is True
    mock_track_skill.assert_called_once_with(EmotionalSkill.CRISIS_REDIRECT.value)
    mock_track_crisis.assert_called_once()


@patch("app.graph.nodes.emotional_router.track_crisis_override")
@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_crisis_override_commit_suicide(mock_track_skill, mock_track_crisis):
    """Test that 'commit suicide' phrasing also triggers CRISIS_REDIRECT and metrics."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    # Phrase reported from production metrics gap
    state = _base_state(
        transcript="I want to commit suicide",
        conversation_count=5,
    )

    result = node(state)

    assert result["skill_id"] == EmotionalSkill.CRISIS_REDIRECT.value
    assert result["had_crisis"] is True
    mock_track_skill.assert_called_once_with(EmotionalSkill.CRISIS_REDIRECT.value)
    mock_track_crisis.assert_called_once()


@patch("app.graph.nodes.emotional_router.track_boundary_override")
@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_boundary_override(mock_track_skill, mock_track_boundary):
    """Test that 'send nudes' triggers BOUNDARY_HOLDING and metrics are tracked."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    state = _base_state(
        transcript="send nudes",
        conversation_count=5,
    )

    result = node(state)

    assert result["skill_id"] == EmotionalSkill.BOUNDARY_HOLDING.value
    assert result["had_boundary"] is True
    mock_track_skill.assert_called_once_with(EmotionalSkill.BOUNDARY_HOLDING.value)
    mock_track_boundary.assert_called_once()


@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_challenging_growth_trust_gate(mock_track_skill):
    """Test that growth cues require conversation_count >= 10 to route to CHALLENGING_GROWTH."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    # Test with conv_count < 10 (should NOT route to CHALLENGING_GROWTH)
    state_low = _base_state(
        transcript="challenge me to grow",
        conversation_count=8,
        tier0_label="growth",
    )
    result_low = node(state_low)
    assert result_low["skill_id"] != EmotionalSkill.CHALLENGING_GROWTH.value

    # Test with conv_count >= 10 (should route to CHALLENGING_GROWTH)
    state_high = _base_state(
        transcript="challenge me to grow",
        conversation_count=10,
        tier0_label="growth",
    )
    result_high = node(state_high)
    assert result_high["skill_id"] == EmotionalSkill.CHALLENGING_GROWTH.value


@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_breakthrough_trust_gate(mock_track_skill):
    """Test that breakthrough cues require conversation_count >= 3 to route to CELEBRATING_BREAKTHROUGH."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    # Test with conv_count < 3 (should NOT route to CELEBRATING_BREAKTHROUGH)
    state_low = _base_state(
        transcript="I just had a breakthrough!",
        conversation_count=2,
        tier0_label="breakthrough",
    )
    result_low = node(state_low)
    assert result_low["skill_id"] != EmotionalSkill.CELEBRATING_BREAKTHROUGH.value

    # Test with conv_count >= 3 (should route to CELEBRATING_BREAKTHROUGH)
    state_high = _base_state(
        transcript="I just had a breakthrough!",
        conversation_count=3,
        tier0_label="breakthrough",
    )
    result_high = node(state_high)
    assert result_high["skill_id"] == EmotionalSkill.CELEBRATING_BREAKTHROUGH.value


@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_fallback_active_listening(mock_track_skill):
    """Test that ambiguous text defaults to ACTIVE_LISTENING."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    state = _base_state(
        transcript="today was a day",
        conversation_count=5,
    )

    result = node(state)

    assert result["skill_id"] == EmotionalSkill.ACTIVE_LISTENING.value
    mock_track_skill.assert_called_once_with(EmotionalSkill.ACTIVE_LISTENING.value)


@patch("app.graph.nodes.emotional_router.track_skill_distribution")
def test_langgraph_integration(mock_track_skill):
    """Test that when current_mode != EMOTIONAL_SUPPORT, routing is skipped (no-op)."""
    node = EmotionalSkillRouterNode(router=route_emotional_skill)

    state = _base_state(
        current_mode=CurrentMode.UTILITY_DIRECT,
        transcript="I feel sad",
    )

    result = node(state)

    # Should not route or track metrics when not in EMOTIONAL_SUPPORT mode
    assert "skill_id" not in result or result.get("skill_id") is None
    mock_track_skill.assert_not_called()
