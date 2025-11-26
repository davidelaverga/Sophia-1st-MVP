"""LangGraph node for routing emotional support turns to specific skills."""

import logging
from typing import Any, Callable, Dict, Optional

from app.obs.metrics import (
    track_boundary_override,
    track_crisis_override,
    track_skill_distribution,
)
from app.routing.emotional_router import (
    ConversationMeta,
    EmotionalRoutingResult,
    EmotionalSkill,
    route_emotional_skill,
)
from app.routing.models import CurrentMode

logger = logging.getLogger(__name__)


class EmotionalSkillRouterNode:
    """Routes emotional-support turns to a concrete emotional skill."""

    def __init__(
        self,
        router: Callable[
            [str, ConversationMeta, Optional[str]], EmotionalRoutingResult
        ] = route_emotional_skill,
    ):
        self._router = router

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route to an emotional skill when current_mode is EMOTIONAL_SUPPORT."""
        # Ensure downstream nodes always see explicit flags
        state.setdefault("had_crisis", False)
        state.setdefault("had_boundary", False)

        if not self._is_emotional_mode(state.get("current_mode")):
            return state

        meta = ConversationMeta(
            conversation_count=self._safe_int(state.get("conversation_count", 0)),
            last_skill=state.get("last_skill"),
            user_id=state.get("user_id"),
        )
        message = self._extract_message(state)
        tier0_label = state.get("tier0_label")

        result = self._router(message, meta, tier0_label=tier0_label)

        skill = result.skill

        # Track skill distribution metrics
        track_skill_distribution(skill.value)

        # Track crisis and boundary overrides (required for customer validation)
        if skill == EmotionalSkill.CRISIS_REDIRECT:
            track_crisis_override()
        elif skill == EmotionalSkill.BOUNDARY_HOLDING:
            track_boundary_override()

        state["skill_id"] = skill.value
        state["skill_variant"] = result.tier0_label
        state["skill_reasoning"] = result.reasoning
        state["last_skill"] = skill.value
        state["had_crisis"] = state["had_crisis"] or (
            skill == EmotionalSkill.CRISIS_REDIRECT
        )
        state["had_boundary"] = state["had_boundary"] or (
            skill == EmotionalSkill.BOUNDARY_HOLDING
        )

        logger.info(
            "EmotionalSkillRouterNode routed to %s (variant=%s)",
            result.skill.value,
            result.tier0_label,
        )

        return state

    @staticmethod
    def _extract_message(state: Dict[str, Any]) -> str:
        """Pull the user-facing message text from common state keys."""
        for key in ("transcript", "user_message", "text"):
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _is_emotional_mode(mode_value: Any) -> bool:
        if isinstance(mode_value, CurrentMode):
            return mode_value == CurrentMode.EMOTIONAL_SUPPORT
        if isinstance(mode_value, str):
            return mode_value.lower() == CurrentMode.EMOTIONAL_SUPPORT.value
        return False
