import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Pattern, Set

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarkerDefinition:
    name: str
    patterns: List[Pattern[str]] = field(default_factory=list)
    exceptions: List[Pattern[str]] = field(default_factory=list)


@dataclass(frozen=True)
class MarkerMatch:
    crisis_markers: Set[str] = field(default_factory=set)
    boundary_markers: Set[str] = field(default_factory=set)


# Basic stopwords used to build a looser pattern matcher without hardcoding
# marker keywords. This helps tolerate small wording changes (articles, fillers).
_STOPWORDS = {
    "i",
    "im",
    "i'm",
    "ill",
    "i'll",
    "ive",
    "i've",
    "to",
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "of",
    "in",
    "on",
    "at",
    "my",
    "me",
    "am",
    "is",
    "are",
    "its",
    "it's",
    "it",
    "this",
    "that",
}


def _marker_file_path() -> Path:
    """Resolve the centralized marker file."""
    root = Path(__file__).resolve().parents[2]
    path = root / "content_markers_v2-1.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Marker file not found at {path}")
    return path


def _clean_pattern(raw: str) -> str:
    """
    Normalize pattern strings from YAML.

    YAML escapes like "\\b" are loaded as backspace characters; convert them
    back to regex boundaries. Strip placeholders such as "[person]" that
    won't appear verbatim in user text.
    """
    if not isinstance(raw, str):
        return ""

    cleaned = raw.replace("\x08", r"\b").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\[.*?]", " ", cleaned).strip()
    return cleaned


def _looks_like_regex(pattern: str) -> bool:
    """Heuristic: decide if a pattern should be treated as regex."""
    regex_indicators = ("\\", "^", "$", "|", "[", "]", "(", ")", "{", "}", "*", "+")
    return any(indicator in pattern for indicator in regex_indicators)


def _tokenize(text: str) -> List[str]:
    tokens = re.split(r"\s+", text.lower())
    return [t for t in tokens if t]


def _phrase_regex(tokens: List[str], loose: bool = False) -> Pattern[str]:
    if loose:
        body = r"\b.*?\b".join(re.escape(token) for token in tokens)
    else:
        body = r"\s+".join(re.escape(token) for token in tokens)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


def _compile_patterns(
    patterns: Iterable[str],
    treat_as_regex: bool = False,
    allow_single_token_loose: bool = False,
) -> List[Pattern[str]]:
    compiled: List[Pattern[str]] = []

    for raw in patterns or []:
        pattern = _clean_pattern(raw)
        if not pattern:
            continue

        is_regex = treat_as_regex or _looks_like_regex(pattern)

        if is_regex:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
                continue
            except re.error:
                logger.warning(
                    "Invalid regex pattern '%s'; falling back to phrase match.", pattern
                )

        tokens = _tokenize(pattern)
        if not tokens:
            continue

        try:
            compiled.append(_phrase_regex(tokens))
        except re.error as exc:
            logger.debug(
                "Could not compile strict phrase regex for '%s': %s", pattern, exc
            )
            continue

        # Looser variant tolerating missing filler words like articles/prepositions.
        loose_tokens = [t for t in tokens if t not in _STOPWORDS]
        if len(loose_tokens) >= 2:
            try:
                compiled.append(_phrase_regex(loose_tokens, loose=True))
            except re.error as exc:
                logger.debug(
                    "Could not compile loose phrase regex for '%s': %s", pattern, exc
                )
        elif (
            allow_single_token_loose
            and len(loose_tokens) == 1
            and len(tokens) >= 2
            and len(loose_tokens[0]) >= 4
        ):
            try:
                compiled.append(_phrase_regex(loose_tokens, loose=True))
            except re.error as exc:
                logger.debug(
                    "Could not compile single-token loose regex for '%s': %s",
                    pattern,
                    exc,
                )

    return compiled


def _collect_marker_definitions(
    section: Dict[str, Any], allow_single_token_loose: bool = False
) -> Dict[str, MarkerDefinition]:
    """
    Convert a YAML marker section into compiled marker definitions keyed by name.
    Alias markers inherit patterns from their targets so the matcher remains
    in sync when the YAML taxonomy changes.
    """
    definitions: Dict[str, MarkerDefinition] = {}

    for name, data in section.items():
        if not isinstance(data, dict):
            continue

        patterns = data.get("patterns")
        exceptions = data.get("exceptions")
        regex_anchored = bool(data.get("regex_anchored"))

        compiled_patterns = _compile_patterns(
            patterns or [],
            treat_as_regex=regex_anchored,
            allow_single_token_loose=allow_single_token_loose,
        )
        compiled_exceptions = _compile_patterns(exceptions or [], treat_as_regex=True)

        if compiled_patterns:
            definitions[name] = MarkerDefinition(
                name=name, patterns=compiled_patterns, exceptions=compiled_exceptions
            )

    # Resolve aliases after base patterns are available.
    for name, data in section.items():
        if not isinstance(data, dict):
            continue

        alias_for = data.get("alias_for") or []
        if not alias_for:
            continue

        aggregated_patterns: List[Pattern[str]] = []
        aggregated_exceptions: List[Pattern[str]] = []

        existing = definitions.get(name)
        if existing:
            aggregated_patterns.extend(existing.patterns)
            aggregated_exceptions.extend(existing.exceptions)

        for target in alias_for:
            ref = definitions.get(target)
            if not ref:
                continue
            aggregated_patterns.extend(ref.patterns)
            aggregated_exceptions.extend(ref.exceptions)

        if aggregated_patterns:
            definitions[name] = MarkerDefinition(
                name=name,
                patterns=aggregated_patterns,
                exceptions=aggregated_exceptions,
            )

    return definitions


@lru_cache(maxsize=1)
def _load_marker_definitions() -> Dict[str, Dict[str, MarkerDefinition]]:
    """Load and compile boundary/crisis marker definitions from the YAML file."""
    data: Dict[str, Any] = {}
    try:
        path = _marker_file_path()
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        logger.error("Marker taxonomy file missing: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to load marker taxonomy: %s", exc)

    boundary_section = data.get("boundary_markers") or {}
    crisis_section = data.get("crisis_markers") or {}

    return {
        "boundary": _collect_marker_definitions(boundary_section),
        "crisis": _collect_marker_definitions(
            crisis_section, allow_single_token_loose=True
        ),
    }


def _match_group(text: str, markers: Dict[str, MarkerDefinition]) -> Set[str]:
    matches: Set[str] = set()
    if not text:
        return matches

    lowered = text.lower()
    for name, definition in markers.items():
        if definition.exceptions and any(
            exc.search(lowered) for exc in definition.exceptions
        ):
            continue

        if any(pattern.search(lowered) for pattern in definition.patterns):
            matches.add(name)

    return matches


def match_markers(text: str) -> MarkerMatch:
    """
    Lightweight keyword matcher for crisis/boundary markers.

    Returns:
        MarkerMatch with sets of marker names that matched the provided text.
    """
    definitions = _load_marker_definitions()
    crisis_matches = _match_group(text, definitions.get("crisis", {}))
    boundary_matches = _match_group(text, definitions.get("boundary", {}))

    return MarkerMatch(crisis_markers=crisis_matches, boundary_markers=boundary_matches)
