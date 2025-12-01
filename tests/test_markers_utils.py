import re

from app.routing import markers
from app.routing.markers import MarkerDefinition


def test_clean_pattern_handles_non_string_and_boundaries():
    assert markers._clean_pattern(None) == ""
    cleaned = markers._clean_pattern("\\bgun\\b [person]")
    assert "\\bgun\\b" in cleaned
    assert "[" not in cleaned


def test_compile_patterns_falls_back_on_invalid_regex(caplog):
    caplog.set_level("WARNING")
    compiled = markers._compile_patterns(["[unclosed"], treat_as_regex=True)
    # Should log a warning and still return a compiled pattern via phrase fallback
    assert compiled
    assert any("Invalid regex pattern" in rec.message for rec in caplog.records)


def test_compile_patterns_allows_loose_single_token():
    # allow_single_token_loose should add a second pattern when one loose token remains
    compiled = markers._compile_patterns(
        ["I really need help"], allow_single_token_loose=True, treat_as_regex=False
    )
    assert len(compiled) >= 1


def test_collect_marker_definitions_resolves_aliases():
    section = {
        "base": {"patterns": ["hello world"]},
        "alias": {"alias_for": ["base"]},
    }
    definitions = markers._collect_marker_definitions(section)
    assert "alias" in definitions
    assert definitions["alias"].patterns  # inherits patterns from base


def test_match_group_respects_exceptions():
    definition = MarkerDefinition(
        name="test",
        patterns=[re.compile(r"forbidden")],
        exceptions=[re.compile(r"forbidden phrase")],
    )
    # Exception matches -> no hit
    assert not markers._match_group("forbidden phrase", {"test": definition})
    # Without exception text should match
    assert markers._match_group("totally forbidden", {"test": definition}) == {"test"}
