"""
Unit tests for Task #42731 - Intent/Mode classification and Prometheus metrics.

Tests:
- test_intent_emotional_vs_utility: emotional phrases → EMOTIONAL
- test_utility_direct_vs_light: greetings → DIRECT, questions → LIGHT
- test_explicit_reflection_agentic: reflection keywords → AGENTIC
- test_langgraph_node_integration: state populated correctly
- test_metrics_incremented: Prometheus counters work
"""

from types import SimpleNamespace

import pytest

import app.routing.intent_router as intent_router
from app.routing.intent_router import classify_intent_and_mode
from app.routing.utility_router import classify_utility_path
from app.routing.models import Intent, CurrentMode, UtilityPath
from app.obs.metrics import (
    boundary_override_total,
    crisis_override_total,
    EMOTIONAL_SKILL_IDS,
    intent_total,
    skill_total,
    mode_total,
    utility_path_total,
    track_boundary_override,
    track_crisis_override,
    track_intent,
    track_skill_distribution,
    track_mode,
    track_utility_path,
)


class TestIntentEmotionalVsUtility:
    """Test emotional vs utility intent classification."""

    @pytest.mark.asyncio
    async def test_emotional_phrases_classified_as_emotional(self):
        """Emotional phrases like 'I feel sad' should route to EMOTIONAL_SUPPORT."""
        emotional_messages = [
            "I feel so sad today",
            "I'm scared about the future",
            "I'm afraid of failing",
            "I'm feeling lost and anxious",
        ]

        for msg in emotional_messages:
            result = await classify_intent_and_mode(msg, session_id="test-session")
            assert result.intent == Intent.EMOTIONAL_SUPPORT, (
                f"Message '{msg}' should be EMOTIONAL_SUPPORT, got {result.intent}"
            )
            assert result.current_mode == CurrentMode.EMOTIONAL_SUPPORT
            assert result.utility_path is None

    @pytest.mark.asyncio
    async def test_utility_phrases_classified_as_utility(self):
        """Utility phrases like 'explain X' should route to UTILITY."""
        utility_messages = [
            "Explain how photosynthesis works",
            "Summarize the main points",
            "How do I fix this bug?",
            "Help me write a cover letter",
        ]

        for msg in utility_messages:
            result = await classify_intent_and_mode(msg, session_id="test-session")
            assert result.intent == Intent.UTILITY, (
                f"Message '{msg}' should be UTILITY, got {result.intent}"
            )
            assert result.current_mode in [
                CurrentMode.UTILITY_DIRECT,
                CurrentMode.UTILITY_LIGHT,
                CurrentMode.UTILITY_AGENTIC,
            ]
            assert result.utility_path is not None

    @pytest.mark.asyncio
    async def test_ambiguous_greeting_question_biases_toward_utility(self, monkeypatch):
        """Ambiguous greeting + question should bias toward UTILITY (utility-first ambiguity)."""

        async def fake_tier0(text, prosody=None):
            return SimpleNamespace(
                type=intent_router.INTENT_GREETING, emotion="neutral", confidence=0.8
            )

    @pytest.mark.asyncio
    async def test_greeting_ambiguous_biases_to_direct_utility(self):
        """Greetings with slight ambiguity should route to direct utility, not emotional."""
        msg = "Hello, Sofia. How are you today?"

        result = await classify_intent_and_mode(msg, session_id="greeting-test")

        assert result.intent == Intent.UTILITY
        assert result.current_mode == CurrentMode.UTILITY_DIRECT
        assert result.utility_path == UtilityPath.DIRECT


class TestUtilityDirectVsLight:
    """Test utility path classification between DIRECT and LIGHT."""

    def test_greetings_routed_to_direct(self):
        """Greetings should route to DIRECT utility path."""
        greetings = [
            "hi",
            "hello",
            "hey there",
            "good morning",
            "thanks",
            "thank you",
            "goodbye",
        ]

        for greeting in greetings:
            result = classify_utility_path(greeting)
            assert result.path == UtilityPath.DIRECT, (
                f"Greeting '{greeting}' should be DIRECT, got {result.path}"
            )
            assert result.confidence > 0.7

    def test_short_questions_routed_to_direct(self):
        """Short factual questions (<12 words) should route to DIRECT."""
        short_questions = [
            "What time is it?",
            "When is the meeting?",
            "How's the weather?",
            "Who is the president?",
        ]

        for q in short_questions:
            result = classify_utility_path(q)
            assert result.path == UtilityPath.DIRECT, (
                f"Short question '{q}' should be DIRECT, got {result.path}"
            )

    def test_context_heavy_routed_to_light(self):
        """Context-heavy requests should route to LIGHT."""
        context_heavy = [
            "Explain the theory of relativity in detail",
            "Help me plan my vacation to Japan",
            "Walk me through setting up a server",
            "Draft a business proposal for me",
        ]

        for msg in context_heavy:
            result = classify_utility_path(msg)
            assert result.path == UtilityPath.LIGHT, (
                f"Context-heavy '{msg}' should be LIGHT, got {result.path}"
            )

    def test_default_to_light(self):
        """Messages without specific cues should default to LIGHT."""
        default_messages = [
            "Tell me about quantum computing",
            "I need some information about machine learning",
        ]

        for msg in default_messages:
            result = classify_utility_path(msg)
            assert result.path == UtilityPath.LIGHT, (
                f"Default message '{msg}' should be LIGHT, got {result.path}"
            )


class TestExplicitReflectionAgentic:
    """Test reflection keywords route to AGENTIC path."""

    def test_reflection_keywords_routed_to_agentic(self):
        """Explicit reflection cues should route to AGENTIC."""
        reflection_messages = [
            "Create a reflection card for this",
            "Turn this into a reflection prompt",
            "Make this a reflection",
            "I need a reflection card",
            "Generate a reflection prompt for reflection",
        ]

        for msg in reflection_messages:
            result = classify_utility_path(msg)
            assert result.path == UtilityPath.AGENTIC, (
                f"Reflection message '{msg}' should be AGENTIC, got {result.path}"
            )
            assert result.confidence >= 0.9

    def test_non_reflection_not_agentic(self):
        """Messages without reflection cues should NOT be AGENTIC."""
        non_reflection = [
            "Explain this concept",
            "Help me write code",
            "What does this mean?",
        ]

        for msg in non_reflection:
            result = classify_utility_path(msg)
            assert result.path != UtilityPath.AGENTIC, (
                f"Non-reflection '{msg}' should not be AGENTIC"
            )


class TestLangGraphNodeIntegration:
    """Test that state is populated correctly in LangGraph node integration."""

    @pytest.mark.asyncio
    async def test_intent_result_populates_state_correctly(self):
        """Verify IntentResult fields are correctly populated."""
        msg = "I feel anxious about my presentation"
        result = await classify_intent_and_mode(msg, session_id="test-123")

        # Check all required fields
        assert isinstance(result.intent, Intent)
        assert isinstance(result.current_mode, CurrentMode)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0

        # For emotional intent, utility_path should be None
        if result.intent == Intent.EMOTIONAL_SUPPORT:
            assert result.utility_path is None
        else:
            assert result.utility_path is not None
            assert isinstance(result.utility_path, UtilityPath)

    @pytest.mark.asyncio
    async def test_utility_result_has_all_fields(self):
        """Verify utility intent has utility_path populated."""
        msg = "Explain how DNS works"
        result = await classify_intent_and_mode(msg, session_id="test-456")

        if result.intent == Intent.UTILITY:
            assert result.utility_path is not None
            assert result.utility_path in [
                UtilityPath.DIRECT,
                UtilityPath.LIGHT,
                UtilityPath.AGENTIC,
            ]
            # Mode should match utility path
            if result.utility_path == UtilityPath.DIRECT:
                assert result.current_mode == CurrentMode.UTILITY_DIRECT
            elif result.utility_path == UtilityPath.LIGHT:
                assert result.current_mode == CurrentMode.UTILITY_LIGHT
            elif result.utility_path == UtilityPath.AGENTIC:
                assert result.current_mode == CurrentMode.UTILITY_AGENTIC


class TestMetricsIncremented:
    """Test that Prometheus metrics are correctly incremented."""

    def get_metric_value(self, metric, labels):
        """Helper to get current metric value from Prometheus registry."""
        for sample in metric.collect()[0].samples:
            if sample.labels == labels and sample.name.endswith("_total"):
                return sample.value
        return 0

    def test_track_intent_increments_counter(self):
        """Verify track_intent() increments intent_total counter."""
        initial_emotional = self.get_metric_value(
            intent_total, {"intent": "emotional_support"}
        )
        initial_utility = self.get_metric_value(intent_total, {"intent": "utility"})

        track_intent("emotional_support")
        track_intent("utility")
        track_intent("utility")

        final_emotional = self.get_metric_value(
            intent_total, {"intent": "emotional_support"}
        )
        final_utility = self.get_metric_value(intent_total, {"intent": "utility"})

        assert final_emotional == initial_emotional + 1
        assert final_utility == initial_utility + 2

    def test_track_mode_increments_counter(self):
        """Verify track_mode() increments mode_total counter."""
        initial_emotional = self.get_metric_value(
            mode_total, {"mode": "emotional_support"}
        )
        initial_direct = self.get_metric_value(mode_total, {"mode": "utility_direct"})

        track_mode("emotional_support")
        track_mode("utility_direct")
        track_mode("utility_direct")

        final_emotional = self.get_metric_value(
            mode_total, {"mode": "emotional_support"}
        )
        final_direct = self.get_metric_value(mode_total, {"mode": "utility_direct"})

        assert final_emotional == initial_emotional + 1
        assert final_direct == initial_direct + 2

    def test_track_utility_path_increments_counter(self):
        """Verify track_utility_path() increments utility_path_total counter."""
        initial_direct = self.get_metric_value(utility_path_total, {"path": "direct"})
        initial_light = self.get_metric_value(utility_path_total, {"path": "light"})
        initial_agentic = self.get_metric_value(utility_path_total, {"path": "agentic"})

        track_utility_path("direct")
        track_utility_path("light")
        track_utility_path("light")
        track_utility_path("agentic")

        final_direct = self.get_metric_value(utility_path_total, {"path": "direct"})
        final_light = self.get_metric_value(utility_path_total, {"path": "light"})
        final_agentic = self.get_metric_value(utility_path_total, {"path": "agentic"})

        assert final_direct == initial_direct + 1
        assert final_light == initial_light + 2
        assert final_agentic == initial_agentic + 1

    def test_track_skill_distribution_increments_counter(self):
        """Verify track_skill_distribution() increments per-skill counters."""
        initial_counts = {
            skill_id: self.get_metric_value(skill_total, {"skill_id": skill_id})
            for skill_id in EMOTIONAL_SKILL_IDS
        }

        for skill_id in EMOTIONAL_SKILL_IDS:
            track_skill_distribution(skill_id)

        for skill_id in EMOTIONAL_SKILL_IDS:
            final_count = self.get_metric_value(skill_total, {"skill_id": skill_id})
            assert final_count == initial_counts[skill_id] + 1

    def test_skill_labels_initialized_for_all_emotional_skills(self):
        """Ensure all emotional skills have a metric label registered."""
        skill_labels = {
            sample.labels.get("skill_id")
            for sample in skill_total.collect()[0].samples
            if sample.name.endswith("_total")
        }

        assert set(EMOTIONAL_SKILL_IDS).issubset(skill_labels)

    def test_crisis_and_boundary_override_counters_increment(self):
        """Verify crisis_override_total and boundary_override_total increment."""
        initial_crisis = self.get_metric_value(crisis_override_total, {})
        initial_boundary = self.get_metric_value(boundary_override_total, {})

        track_crisis_override()
        track_boundary_override()

        final_crisis = self.get_metric_value(crisis_override_total, {})
        final_boundary = self.get_metric_value(boundary_override_total, {})

        assert final_crisis == initial_crisis + 1
        assert final_boundary == initial_boundary + 1

    @pytest.mark.asyncio
    async def test_classify_intent_triggers_metrics(self):
        """Verify classify_intent_and_mode() actually calls metrics tracking."""
        initial_intent_emotional = self.get_metric_value(
            intent_total, {"intent": "emotional_support"}
        )
        initial_mode_emotional = self.get_metric_value(
            mode_total, {"mode": "emotional_support"}
        )

        # Classify an emotional message
        await classify_intent_and_mode("I feel so anxious", session_id="metrics-test")

        final_intent_emotional = self.get_metric_value(
            intent_total, {"intent": "emotional_support"}
        )
        final_mode_emotional = self.get_metric_value(
            mode_total, {"mode": "emotional_support"}
        )

        # Should have incremented
        assert final_intent_emotional > initial_intent_emotional
        assert final_mode_emotional > initial_mode_emotional

    @pytest.mark.asyncio
    async def test_utility_classification_triggers_all_metrics(self):
        """Verify utility classification increments intent, mode, AND utility_path."""
        initial_intent = self.get_metric_value(intent_total, {"intent": "utility"})
        initial_mode_light = self.get_metric_value(
            mode_total, {"mode": "utility_light"}
        )
        initial_path_light = self.get_metric_value(
            utility_path_total, {"path": "light"}
        )

        # Classify a utility message that should go to LIGHT
        await classify_intent_and_mode(
            "Explain quantum entanglement", session_id="utility-test"
        )

        final_intent = self.get_metric_value(intent_total, {"intent": "utility"})
        final_mode_light = self.get_metric_value(mode_total, {"mode": "utility_light"})
        final_path_light = self.get_metric_value(utility_path_total, {"path": "light"})

        # All three should increment
        assert final_intent > initial_intent
        assert final_mode_light > initial_mode_light
        assert final_path_light > initial_path_light
