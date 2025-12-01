"""Skill routing models for Sophia's conversational AI.

This module defines the available skills that Sophia can route conversations to,
along with the routing result structure.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SkillId(str, Enum):
    """Available skills for conversation routing.

    Each skill represents a specialized capability that Sophia can handle.
    """

    GREETING = "greeting"
    """Handle greetings and initial user interactions"""

    DEFI_BASICS = "defi_basics"
    """Teach fundamental DeFi concepts (what is DeFi, blockchain basics, etc.)"""

    DEFI_ADVANCED = "defi_advanced"
    """Explain advanced DeFi topics (governance, tokenomics, metrics, etc.)"""

    YIELD_STAKING = "yield_staking"
    """Discuss yield farming, staking, and liquidity provision"""

    TRADING = "trading"
    """Provide guidance on trading, swaps, and market analysis"""

    RISK_SAFETY = "risk_safety"
    """Address security concerns, risk management, and safety practices"""

    EMOTIONAL_SUPPORT = "emotional_support"
    """Provide empathetic responses to users sharing emotions or concerns"""

    CRISIS_INTERVENTION = "crisis_intervention"
    """Handle crisis situations requiring immediate empathetic intervention"""


@dataclass
class SkillRouteResult:
    """Result of skill routing decision.

    Contains the selected skill, optional variant for future extensibility,
    reasoning behind the selection, and confidence score.
    """

    skill_id: SkillId
    """The skill selected for handling this conversation turn"""

    skill_variant: Optional[str] = None
    """Optional variant of the skill (e.g., 'FIERCE' or 'TENDER' in Phase 2)"""

    reasoning: str = ""
    """Human-readable explanation of why this skill was selected"""

    confidence: float = 1.0
    """Confidence score for this routing decision (0.0 to 1.0)"""
