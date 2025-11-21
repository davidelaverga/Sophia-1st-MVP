import re

from app.routing.models import UtilityPath, UtilityPathResult

REFLECTION_CUES = (
    r"\breflection card\b",
    r"\breflection prompt\b",
    r"\bturn (?:this|it) into (?:a )?reflection\b",
    r"\bmake (?:this|it) a reflection\b",
    r"\bfor reflection\b",
)

GREETING_CUES = (
    r"^\s*(hi|hello|hey|yo)\b",
    r"\bgood (?:morning|evening|night)\b",
    r"\bbye\b",
    r"\bgoodbye\b",
    r"\bsee you\b",
    r"\bthanks\b",
    r"\bthank you\b",
)

SHORT_FACTUAL_CUES = (
    r"\bwhat\b",
    r"\bwhen\b",
    r"\bwhere\b",
    r"\bhow\b",
    r"\bwho\b",
    r"\btime\b",
    r"\bdate\b",
    r"\bweather\b",
    r"\bmeaning\b",
)

CONTEXT_HEAVY_CUES = (
    r"\bexplain\b",
    r"\bplan\b",
    r"\bhelp me\b",
    r"\bwalk me\b",
    r"\bguide me\b",
    r"\bdraft\b",
    r"\bwrite\b",
)


def _has_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def classify_utility_path(user_message: str) -> UtilityPathResult:
    """
    Lightweight routing for utility turns based on heuristics:
    - DIRECT: trivial greetings/closings or <12 word factoid queries.
    - LIGHT: default planning/explanation path when no explicit cues.
    - AGENTIC: explicit reflection card requests.
    """

    text = (user_message or "").strip()
    normalized = text.lower()
    word_count = _count_words(normalized)

    if not text:
        reasoning = "Empty message defaults to light utility path."
        return UtilityPathResult(UtilityPath.LIGHT, 0.5, reasoning)

    if _has_pattern(normalized, REFLECTION_CUES):
        reasoning = "Reflection cue detected; routing to agentic reflection workflow."
        return UtilityPathResult(UtilityPath.AGENTIC, 0.9, reasoning)

    if _has_pattern(normalized, GREETING_CUES):
        reasoning = "Greeting/closing detected; using direct end-to-end utility path."
        confidence = 0.82 if word_count <= 4 else 0.74
        return UtilityPathResult(UtilityPath.DIRECT, confidence, reasoning)

    if word_count and word_count < 12:
        if _has_pattern(normalized, CONTEXT_HEAVY_CUES):
            reasoning = (
                "Context-heavy utility cue (plan/explain/write); using light path."
            )
            return UtilityPathResult(UtilityPath.LIGHT, 0.7, reasoning)

        is_question_like = "?" in normalized or _has_pattern(
            normalized, SHORT_FACTUAL_CUES
        )
        is_trivial_statement = word_count <= 3

        if is_question_like or is_trivial_statement:
            reasoning = (
                "Under 12 words with a simple query; choosing fastest direct path."
            )
            confidence = 0.78 if word_count <= 6 else 0.7
            return UtilityPathResult(UtilityPath.DIRECT, confidence, reasoning)

    reasoning = "No reflection cue and not a trivial query; using light utility flow."
    return UtilityPathResult(UtilityPath.LIGHT, 0.65, reasoning)
