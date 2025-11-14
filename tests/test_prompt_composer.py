"""Unit tests for PromptComposer (Task #42597)."""

import pytest
from app.services.prompt_composer import PromptComposer


class TestPromptComposer:
    """Test PromptComposer functionality"""

    @pytest.fixture
    def mock_base_identity(self):
        return """# Sophia - DeFi Mentor AI

You are Sophia, a friendly and knowledgeable DeFi mentor.

## Core Principles
1. Education over speculation
2. Risk awareness
3. User safety
"""

    @pytest.fixture
    def composer_with_file(self, tmp_path, mock_base_identity):
        """PromptComposer with real file"""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        base_identity_file = prompts_dir / "base_identity.md"
        base_identity_file.write_text(mock_base_identity)

        composer = PromptComposer(prompts_dir=str(prompts_dir))
        return composer

    @pytest.fixture
    def composer_without_file(self, tmp_path):
        """PromptComposer without base_identity.md file"""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        composer = PromptComposer(prompts_dir=str(prompts_dir))
        return composer

    def test_initialization_with_file(self, composer_with_file):
        """Test composer initializes with base identity file"""
        assert composer_with_file._base_identity is not None
        assert "Sophia" in composer_with_file._base_identity
        assert composer_with_file._last_reload is not None

    def test_initialization_without_file(self, composer_without_file):
        """Test composer falls back when file missing"""
        assert composer_without_file._base_identity is not None
        assert "Sophia" in composer_without_file._base_identity
        assert (
            "fallback" in composer_without_file._base_identity.lower()
            or "DeFi" in composer_without_file._base_identity
        )

    def test_reload_prompts_success(self, composer_with_file):
        """Test successful prompt reload"""
        result = composer_with_file.reload_prompts()
        assert result is True
        assert composer_with_file._base_identity is not None

    def test_reload_prompts_file_not_found(self, composer_without_file):
        """Test reload when file not found"""
        result = composer_without_file.reload_prompts()
        assert result is False
        # Should still have fallback identity
        assert composer_without_file._base_identity is not None

    def test_compose_basic_prompt(self, composer_with_file):
        """Test composing basic prompt without context"""
        prompt = composer_with_file.compose_system_prompt()
        assert "Sophia" in prompt
        assert "DeFi" in prompt

    def test_compose_with_memory_context(self, composer_with_file):
        """Test composing prompt with memory context"""
        memory_context = {
            "memories": [
                {
                    "text": "User prefers low-risk strategies",
                    "type": "preference",
                    "relevance": 0.95,
                },
                {
                    "text": "User asked about staking before",
                    "type": "context",
                    "relevance": 0.85,
                },
            ],
            "memory_summary": "2 memories retrieved",
        }

        prompt = composer_with_file.compose_system_prompt(memory_context=memory_context)

        assert "Sophia" in prompt
        assert "Recent Relevant Memories" in prompt
        assert "low-risk strategies" in prompt
        assert "staking" in prompt
        assert "PREFERENCE" in prompt  # Memory type should be uppercased

    def test_compose_with_user_emotion(self, composer_with_file):
        """Test composing prompt with user emotion"""
        prompt = composer_with_file.compose_system_prompt(user_emotion="anxious")

        assert "Sophia" in prompt
        assert "anxious" in prompt
        assert "emotional" in prompt.lower()

    def test_compose_with_additional_context(self, composer_with_file):
        """Test composing prompt with additional context"""
        prompt = composer_with_file.compose_system_prompt(
            additional_context="User is new to DeFi"
        )

        assert "Sophia" in prompt
        assert "Additional Context" in prompt
        assert "new to DeFi" in prompt

    def test_compose_full_context(self, composer_with_file):
        """Test composing prompt with all contexts"""
        memory_context = {
            "memories": [
                {
                    "text": "User likes Ethereum",
                    "type": "preference",
                    "relevance": 0.9,
                }
            ],
            "memory_summary": "1 memory",
        }

        prompt = composer_with_file.compose_system_prompt(
            memory_context=memory_context,
            user_emotion="excited",
            additional_context="User wants to learn about yield farming",
        )

        assert "Sophia" in prompt
        assert "Recent Relevant Memories" in prompt
        assert "Ethereum" in prompt
        assert "excited" in prompt
        assert "yield farming" in prompt

    def test_get_base_identity(self, composer_with_file):
        """Test getting raw base identity"""
        identity = composer_with_file.get_base_identity()
        assert "Sophia" in identity
        assert "DeFi" in identity

    def test_get_reload_status(self, composer_with_file):
        """Test getting reload status"""
        status = composer_with_file.get_reload_status()

        assert "last_reload" in status
        assert status["base_identity_loaded"] is True
        assert "base_identity_file" in status
        assert status["file_exists"] is True
        assert status["file_size"] > 0

    def test_empty_memories_not_included(self, composer_with_file):
        """Test that empty memories don't add memory section"""
        memory_context = {
            "memories": [],
            "memory_summary": "No memories",
        }

        prompt = composer_with_file.compose_system_prompt(memory_context=memory_context)

        assert "Recent Relevant Memories" not in prompt

    def test_neutral_emotion_not_included(self, composer_with_file):
        """Test that neutral emotion doesn't add emotion section"""
        prompt = composer_with_file.compose_system_prompt(user_emotion="neutral")

        assert "emotional" not in prompt.lower() or "Emotional State" not in prompt

    def test_fallback_identity(self, composer_without_file):
        """Test fallback identity content"""
        identity = composer_without_file._get_fallback_identity()

        assert "Sophia" in identity
        assert "DeFi" in identity
        assert "mentor" in identity.lower()
        assert "50 words" in identity  # Brevity requirement
