from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Intent(Enum):
    EMOTIONAL_SUPPORT = "emotional_support"
    UTILITY = "utility"


class CurrentMode(Enum):
    EMOTIONAL_SUPPORT = "emotional_support"
    UTILITY_DIRECT = "utility_direct"
    UTILITY_LIGHT = "utility_light"
    UTILITY_AGENTIC = "utility_agentic"


class UtilityPath(Enum):
    DIRECT = "direct"
    LIGHT = "light"
    AGENTIC = "agentic"


@dataclass
class IntentResult:
    intent: Intent
    current_mode: CurrentMode
    utility_path: Optional[UtilityPath]
    confidence: float
    reasoning: Optional[str] = None


@dataclass
class UtilityPathResult:
    path: UtilityPath
    confidence: float
    reasoning: str
