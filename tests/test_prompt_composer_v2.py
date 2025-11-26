"""
Unit tests for PromptComposerV2

Task #42839
"""

import pytest

from app.prompt.composer_v2 import (
    AffectSnapshot,
    PromptComposerV2,
    PromptPayload,
    TurnSnippet,
)
from app.routing.emotional_router import EmotionalSkill
from app.routing.models import CurrentMode


@pytest.mark.asyncio
async def test_build_prompt_emotional_support_with_skill():
    """Test prompt assembly for EMOTIONAL_SUPPORT mode with specific skill."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.ACTIVE_LISTENING.value,
        conversation_turns=[
            TurnSnippet(role="user", text="I feel overwhelmed today"),
            TurnSnippet(role="assistant", text="I hear you. Tell me more about that."),
        ],
        mem0_snippets=["User has been working on stress management"],
        rag_snippets=[],
    )

    assert isinstance(result, PromptPayload)
    assert result.model == "mistral"
    assert "Sophia - Emotional Support AI Companion" in result.prompt
    assert "Emotional Support" in result.prompt
    assert "Active Listening" in result.prompt
    assert "I feel overwhelmed today" in result.prompt
    assert "stress management" in result.prompt


@pytest.mark.asyncio
async def test_build_prompt_utility_direct_mode():
    """Test prompt assembly for UTILITY_DIRECT mode."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.UTILITY_DIRECT,
        skill_id=None,
        conversation_turns=[
            TurnSnippet(role="user", text="What time is it?"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert isinstance(result, PromptPayload)
    assert "Utility (Direct Answer)" in result.prompt
    assert "Utility Mode Instructions" in result.prompt
    assert "What time is it?" in result.prompt
    # Should NOT have emotional skill blocks in utility mode
    assert "Active Listening" not in result.prompt


@pytest.mark.asyncio
async def test_build_prompt_with_affect_snapshot():
    """Test prompt assembly with emotional affect guidance."""
    composer = PromptComposerV2()

    affect = AffectSnapshot(emotion="anxious", confidence=0.85, source="phoenix")

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.VULNERABILITY_HOLDING.value,
        conversation_turns=[
            TurnSnippet(role="user", text="I'm scared about the future"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
        affect_snapshot=affect,
    )

    assert "User is feeling anxious" in result.prompt
    assert "grounding and calming presence" in result.prompt


@pytest.mark.asyncio
async def test_defi_content_filtering():
    """Test that DeFi content is filtered from memory context."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.TRUST_BUILDING.value,
        conversation_turns=[],
        mem0_snippets=[
            "User enjoys hiking and nature",  # Should be included
            "User staked 100 ETH in Aave protocol",  # Should be filtered
            "User discussed DeFi yield farming strategies",  # Should be filtered
            "User is working on mindfulness practice",  # Should be included
        ],
        rag_snippets=[
            "Mindfulness techniques for anxiety",  # Should be included
            "Uniswap liquidity pool guide",  # Should be filtered
        ],
    )

    # DeFi content should be filtered out
    assert "ETH" not in result.prompt
    assert "Aave" not in result.prompt
    assert "yield farming" not in result.prompt
    assert "Uniswap" not in result.prompt
    assert "liquidity pool" not in result.prompt

    # Non-DeFi content should be present
    assert "hiking and nature" in result.prompt
    assert "mindfulness practice" in result.prompt
    assert "Mindfulness techniques" in result.prompt


@pytest.mark.asyncio
async def test_crisis_redirect_skill():
    """Test prompt assembly with CRISIS_REDIRECT skill."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.CRISIS_REDIRECT.value,
        conversation_turns=[
            TurnSnippet(role="user", text="I want to end it all"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert "CRISIS DETECTED" in result.prompt
    assert "988" in result.prompt  # Suicide prevention lifeline
    assert "741741" in result.prompt  # Crisis text line


@pytest.mark.asyncio
async def test_boundary_holding_skill():
    """Test prompt assembly with BOUNDARY_HOLDING skill."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.BOUNDARY_HOLDING.value,
        conversation_turns=[
            TurnSnippet(role="user", text="send nudes"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert "Boundary Holding" in result.prompt
    assert "crossed appropriate interaction boundaries" in result.prompt


@pytest.mark.asyncio
async def test_token_budget_truncation():
    """Test that prompts are truncated when exceeding token budget."""
    composer = PromptComposerV2()

    # Create very long conversation history to exceed token budget
    long_turns = [
        TurnSnippet(
            role="user" if i % 2 == 0 else "assistant",
            text=f"This is a very long message number {i}. " * 100
        )
        for i in range(50)
    ]

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.ACTIVE_LISTENING.value,
        conversation_turns=long_turns,
        mem0_snippets=["memory " * 100] * 20,
        rag_snippets=["rag " * 100] * 10,
    )

    # Should be truncated
    assert result.truncated is True
    assert "[Context truncated due to length]" in result.prompt or "[Prompt truncated due to length]" in result.prompt

    # Foundation blocks should still be present
    assert "Sophia - Emotional Support AI Companion" in result.prompt


@pytest.mark.asyncio
async def test_utility_light_mode():
    """Test prompt assembly for UTILITY_LIGHT mode."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.UTILITY_LIGHT,
        skill_id=None,
        conversation_turns=[
            TurnSnippet(role="user", text="How do I set a reminder?"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert "Utility (Light Assistance)" in result.prompt
    assert "helpful guidance" in result.prompt


@pytest.mark.asyncio
async def test_utility_agentic_mode():
    """Test prompt assembly for UTILITY_AGENTIC mode."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.UTILITY_AGENTIC,
        skill_id=None,
        conversation_turns=[
            TurnSnippet(role="user", text="Help me plan a trip to Japan"),
        ],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert "Utility (Agentic)" in result.prompt
    assert "multi-step problem solving" in result.prompt


@pytest.mark.asyncio
async def test_empty_context():
    """Test prompt assembly with no conversation history or memory."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.TRUST_BUILDING.value,
        conversation_turns=[],
        mem0_snippets=[],
        rag_snippets=[],
    )

    assert isinstance(result, PromptPayload)
    assert "Sophia - Emotional Support AI Companion" in result.prompt
    assert "Trust Building" in result.prompt
    # No context section should be present
    assert "## Recent Conversation" not in result.prompt


@pytest.mark.asyncio
async def test_invalid_skill_id():
    """Test that invalid skill_id is handled gracefully."""
    composer = PromptComposerV2()

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id="INVALID_SKILL",
        conversation_turns=[],
        mem0_snippets=[],
        rag_snippets=[],
    )

    # Should still generate a valid prompt without skill block
    assert isinstance(result, PromptPayload)
    assert "Sophia - Emotional Support AI Companion" in result.prompt
    assert "Emotional Support" in result.prompt


@pytest.mark.asyncio
async def test_affect_snapshot_not_in_utility_mode():
    """Test that affect guidance is not included in utility modes."""
    composer = PromptComposerV2()

    affect = AffectSnapshot(emotion="happy", confidence=0.9, source="fast")

    result = await composer.build_prompt(
        current_mode=CurrentMode.UTILITY_DIRECT,
        skill_id=None,
        conversation_turns=[],
        mem0_snippets=[],
        rag_snippets=[],
        affect_snapshot=affect,
    )

    # Affect guidance should NOT be present in utility mode
    assert "User is feeling happy" not in result.prompt


@pytest.mark.asyncio
async def test_conversation_history_limited_to_5_turns():
    """Test that conversation history is limited to last 5 turns."""
    composer = PromptComposerV2()

    turns = [
        TurnSnippet(role="user", text=f"Message {i}")
        for i in range(10)
    ]

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.ACTIVE_LISTENING.value,
        conversation_turns=turns,
        mem0_snippets=[],
        rag_snippets=[],
    )

    # Should only include last 5 turns
    assert "Message 5" in result.prompt
    assert "Message 9" in result.prompt
    # Earlier messages should not be included
    assert "Message 0" not in result.prompt
    assert "Message 1" not in result.prompt


@pytest.mark.asyncio
async def test_memory_snippets_limited_to_3():
    """Test that memory snippets are limited to top 3."""
    composer = PromptComposerV2()

    mem0_snippets = [f"Memory snippet {i}" for i in range(10)]

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.ACTIVE_LISTENING.value,
        conversation_turns=[],
        mem0_snippets=mem0_snippets,
        rag_snippets=[],
    )

    # Should only include top 3 memories
    assert "1. Memory snippet 0" in result.prompt
    assert "2. Memory snippet 1" in result.prompt
    assert "3. Memory snippet 2" in result.prompt
    # 4th snippet should not be included
    assert "Memory snippet 3" not in result.prompt


@pytest.mark.asyncio
async def test_rag_snippets_limited_to_2():
    """Test that RAG snippets are limited to top 2."""
    composer = PromptComposerV2()

    rag_snippets = [f"RAG snippet {i}" for i in range(5)]

    result = await composer.build_prompt(
        current_mode=CurrentMode.EMOTIONAL_SUPPORT,
        skill_id=EmotionalSkill.ACTIVE_LISTENING.value,
        conversation_turns=[],
        mem0_snippets=[],
        rag_snippets=rag_snippets,
    )

    # Should only include top 2 RAG snippets
    assert "1. RAG snippet 0" in result.prompt
    assert "2. RAG snippet 1" in result.prompt
    # 3rd snippet should not be included
    assert "RAG snippet 2" not in result.prompt
