from app.graph.nodes.emotional_router import EmotionalSkillRouterNode
from app.routing.emotional_router import (
    EmotionalRoutingResult,
    EmotionalSkill,
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
