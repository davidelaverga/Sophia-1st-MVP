"""Tests for skill routing models."""

from app.routing.skills import SkillId, SkillRouteResult


def test_skill_id_enum_has_8_values():
    """Verify that SkillId enum has exactly 8 skills."""
    skills = list(SkillId)
    assert len(skills) == 8, f"Expected 8 skills, got {len(skills)}"


def test_skill_id_enum_values():
    """Verify all expected skill IDs are present."""
    expected_skills = {
        SkillId.GREETING,
        SkillId.DEFI_BASICS,
        SkillId.DEFI_ADVANCED,
        SkillId.YIELD_STAKING,
        SkillId.TRADING,
        SkillId.RISK_SAFETY,
        SkillId.EMOTIONAL_SUPPORT,
        SkillId.CRISIS_INTERVENTION,
    }
    actual_skills = set(SkillId)
    assert actual_skills == expected_skills


def test_skill_id_string_values():
    """Verify skill IDs have correct string representations."""
    assert SkillId.GREETING == "greeting"
    assert SkillId.DEFI_BASICS == "defi_basics"
    assert SkillId.DEFI_ADVANCED == "defi_advanced"
    assert SkillId.YIELD_STAKING == "yield_staking"
    assert SkillId.TRADING == "trading"
    assert SkillId.RISK_SAFETY == "risk_safety"
    assert SkillId.EMOTIONAL_SUPPORT == "emotional_support"
    assert SkillId.CRISIS_INTERVENTION == "crisis_intervention"


def test_skill_route_result_creation():
    """Test creating SkillRouteResult with all fields."""
    result = SkillRouteResult(
        skill_id=SkillId.DEFI_BASICS,
        skill_variant="TENDER",
        reasoning="User asked about DeFi basics",
        confidence=0.95,
    )

    assert result.skill_id == SkillId.DEFI_BASICS
    assert result.skill_variant == "TENDER"
    assert result.reasoning == "User asked about DeFi basics"
    assert result.confidence == 0.95


def test_skill_route_result_defaults():
    """Test SkillRouteResult with default values."""
    result = SkillRouteResult(skill_id=SkillId.GREETING)

    assert result.skill_id == SkillId.GREETING
    assert result.skill_variant is None
    assert result.reasoning == ""
    assert result.confidence == 1.0


def test_skill_route_result_optional_variant():
    """Test that skill_variant is optional for Phase 2 support."""
    # Should work without variant (Phase 1)
    result1 = SkillRouteResult(
        skill_id=SkillId.EMOTIONAL_SUPPORT,
        reasoning="User sharing emotions",
        confidence=0.88,
    )
    assert result1.skill_variant is None

    # Should work with variant (Phase 2)
    result2 = SkillRouteResult(
        skill_id=SkillId.EMOTIONAL_SUPPORT,
        skill_variant="FIERCE",
        reasoning="User needs direct support",
        confidence=0.92,
    )
    assert result2.skill_variant == "FIERCE"


def test_skill_route_result_confidence_range():
    """Test that confidence can be set in 0.0 to 1.0 range."""
    result_low = SkillRouteResult(skill_id=SkillId.TRADING, confidence=0.0)
    assert result_low.confidence == 0.0

    result_mid = SkillRouteResult(skill_id=SkillId.TRADING, confidence=0.5)
    assert result_mid.confidence == 0.5

    result_high = SkillRouteResult(skill_id=SkillId.TRADING, confidence=1.0)
    assert result_high.confidence == 1.0
