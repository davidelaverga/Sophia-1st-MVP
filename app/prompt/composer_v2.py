"""
Prompt Data Structures and Composer V2 for Sophia

This module defines core data structures for the prompt composition system
and implements the PromptComposerV2 class for dynamic prompt assembly.

"""

from dataclasses import dataclass
from typing import Optional, Literal, List

from app.routing.models import CurrentMode
from app.routing.emotional_router import EmotionalSkill

# Import prompt templates from centralized module (Task #42811)
from app.prompt.templates import (
    SOPHIA_FOUNDATION,
    CURRENT_MODE_BLOCKS,
    SKILL_BLOCKS,
    UTILITY_INSTRUCTIONS,
    AFFECT_GUIDANCE_MAP,
)


@dataclass
class AffectSnapshot:
    """
    Represents an emotional state snapshot at a specific point in time.

    Attributes:
        emotion: Emotion label (e.g., "neutral", "happy", "sad", "anxious")
        confidence: Confidence score between 0.0 and 1.0
        source: Source of the emotion analysis
                - "phoenix": Phoenix emotion analysis
                - "fast": Fast tier-0 classifier
                - None: No emotion data available
    """

    emotion: str
    confidence: float
    source: Optional[Literal["phoenix", "fast"]] = None

    def __post_init__(self):
        """Validate confidence is within valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


@dataclass
class PromptPayload:
    """
    Represents the final prompt payload ready for LLM submission.

    Attributes:
        model: Model identifier (e.g., "mistral-large-latest", "claude-3-haiku")
        prompt: The complete assembled prompt text
        truncated: Whether the prompt was truncated to fit token limits
    """

    model: str
    prompt: str
    truncated: bool = False


@dataclass
class TurnSnippet:
    """
    Represents a single conversational turn in the chat history.

    Attributes:
        role: Speaker role in the conversation
              - "user": User message
              - "assistant": Assistant/Sophia response
        text: The actual message text
    """

    role: Literal["user", "assistant"]
    text: str

    def __post_init__(self):
        """Validate role is valid."""
        if self.role not in ("user", "assistant"):
            raise ValueError(f"role must be 'user' or 'assistant', got '{self.role}'")


# NOTE: Prompt template constants (SOPHIA_FOUNDATION, CURRENT_MODE_BLOCKS,
# SKILL_BLOCKS, UTILITY_INSTRUCTIONS, EMOTIONAL_CONTEXT_INSTRUCTIONS,
# AFFECT_GUIDANCE_TEMPLATE, AFFECT_GUIDANCE_MAP) are now imported from
# app/prompt/templates.py (Task #42811)


# ============================================================================
# PromptComposerV2 - Main prompt assembly class
# ============================================================================


class PromptComposerV2:
    """
    Assembles prompts using tiered composition strategy.

    Tier 1: Foundation identity
    Tier 2: Mode-specific instructions
    Tier 3: Skill or utility instructions
    Tier 4: Conversation and memory context
    Tier 5: Affect-specific guidance (emotional mode only)

    Task #42839
    """

    # Token budget settings
    MAX_TOKENS = 4000  # Conservative limit for Mistral context
    TIER_1_2_3_BUDGET = 1500  # Reserved for foundation + mode + skill
    CONTEXT_BUDGET = 2000  # For conversation history + memory
    AFFECT_BUDGET = 500  # For emotional guidance

    async def build_prompt(
        self,
        *,
        current_mode: CurrentMode,
        skill_id: Optional[str],
        conversation_turns: List[TurnSnippet],
        mem0_snippets: List[str],
        rag_snippets: List[str],
        affect_snapshot: Optional[AffectSnapshot] = None,
    ) -> PromptPayload:
        """
        Build complete prompt from tiered components.

        Args:
            current_mode: Current conversation mode
            skill_id: Emotional skill ID (for EMOTIONAL_SUPPORT mode)
            conversation_turns: Recent conversation history
            mem0_snippets: Memory snippets from Mem0
            rag_snippets: RAG retrieval snippets
            affect_snapshot: User's emotional state (optional)

        Returns:
            PromptPayload with assembled prompt, model ID, and truncation flag
        """
        blocks: List[str] = []

        # Tier 1: Foundation identity
        blocks.append(SOPHIA_FOUNDATION)

        # Tier 2: Mode-specific instructions
        mode_block = CURRENT_MODE_BLOCKS.get(current_mode)
        if mode_block:
            blocks.append(mode_block)

        # Tier 3: Skill or utility instructions
        if current_mode == CurrentMode.EMOTIONAL_SUPPORT and skill_id:
            # Try to parse as EmotionalSkill enum
            try:
                skill_enum = EmotionalSkill(skill_id)
                skill_block = SKILL_BLOCKS.get(skill_enum)
                if skill_block:
                    blocks.append(skill_block)
            except (ValueError, KeyError):
                # If skill_id is invalid, skip skill block
                pass
        else:
            # Non-emotional modes use utility instructions
            blocks.append(UTILITY_INSTRUCTIONS)

        # Tier 4: Conversation and memory context
        context_block = self._build_context_block(
            conversation_turns=conversation_turns,
            mem0_snippets=mem0_snippets,
            rag_snippets=rag_snippets,
        )
        if context_block:
            blocks.append(context_block)

        # Tier 5: Affect-specific guidance (emotional mode only)
        if (
            current_mode == CurrentMode.EMOTIONAL_SUPPORT
            and affect_snapshot
            and affect_snapshot.emotion
        ):
            affect_block = AFFECT_GUIDANCE_MAP.get(
                affect_snapshot.emotion.lower(), AFFECT_GUIDANCE_MAP["neutral"]
            )
            blocks.append(f"\n{affect_block}")

        # Join all blocks
        prompt = "\n\n".join(blocks)

        # Apply token budget
        final_prompt, truncated = self._apply_token_budget(prompt)

        return PromptPayload(
            model="mistral",
            prompt=final_prompt,
            truncated=truncated,
        )

    def _build_context_block(
        self,
        *,
        conversation_turns: List[TurnSnippet],
        mem0_snippets: List[str],
        rag_snippets: List[str],
    ) -> str:
        """
        Build Tier 4 context block from conversation history and memory.

        Args:
            conversation_turns: Recent conversation turns
            mem0_snippets: Memory snippets from Mem0
            rag_snippets: RAG retrieval snippets

        Returns:
            Formatted context block string
        """
        parts = []

        # Recent conversation history
        if conversation_turns:
            parts.append("## Recent Conversation")
            for turn in conversation_turns[-5:]:  # Last 5 turns
                role_label = "User" if turn.role == "user" else "Sophia"
                parts.append(f"**{role_label}**: {turn.text}")

        # Memory context - FILTER OUT DeFi references
        if mem0_snippets:
            # Filter DeFi-related content
            filtered_snippets = self._filter_defi_content(mem0_snippets)
            if filtered_snippets:
                parts.append("\n## Relevant Memories")
                for i, snippet in enumerate(filtered_snippets[:3], 1):  # Top 3
                    parts.append(f"{i}. {snippet}")

        # RAG context - FILTER OUT DeFi references
        if rag_snippets:
            # Filter DeFi-related content
            filtered_rag = self._filter_defi_content(rag_snippets)
            if filtered_rag:
                parts.append("\n## Additional Context")
                for i, snippet in enumerate(filtered_rag[:2], 1):  # Top 2
                    parts.append(f"{i}. {snippet}")

        return "\n".join(parts) if parts else ""

    def _filter_defi_content(self, snippets: List[str]) -> List[str]:
        """
        Filter out DeFi transaction history and protocol references.

        Customer requirement: NO DeFi transactions or protocols in context.

        Args:
            snippets: List of text snippets to filter

        Returns:
            Filtered list with DeFi content removed
        """
        # DeFi keywords to filter out
        defi_keywords = [
            "defi",
            "uniswap",
            "aave",
            "compound",
            "makerdao",
            "yield",
            "staking",
            "liquidity",
            "protocol",
            "transaction",
            "swap",
            "token",
            "eth",
            "btc",
            "blockchain",
            "crypto",
            "wallet",
            "nft",
            "smart contract",
            "gas fee",
            "dex",
            "amm",
        ]

        filtered = []
        for snippet in snippets:
            snippet_lower = snippet.lower()
            # Check if snippet contains DeFi keywords
            contains_defi = any(keyword in snippet_lower for keyword in defi_keywords)
            if not contains_defi:
                filtered.append(snippet)

        return filtered

    def _apply_token_budget(self, prompt: str) -> tuple[str, bool]:
        """
        Apply token budget limits to the prompt.

        Uses simple character-based approximation:
        - 1 token ≈ 4 characters (rough estimate)
        - If prompt exceeds budget, truncate from the middle (context section)

        Args:
            prompt: Full assembled prompt

        Returns:
            Tuple of (truncated_prompt, was_truncated)
        """
        # Rough token estimate: 1 token ≈ 4 characters
        estimated_tokens = len(prompt) // 4

        if estimated_tokens <= self.MAX_TOKENS:
            return prompt, False

        # Prompt is too long - need to truncate
        # Strategy: Keep Tier 1-3 intact, truncate Tier 4 (context)

        # Find context block (starts with "## Recent Conversation")
        context_marker = "## Recent Conversation"
        context_start = prompt.find(context_marker)

        if context_start == -1:
            # No context block found, truncate from end
            max_chars = self.MAX_TOKENS * 4
            return prompt[:max_chars] + "\n\n[Prompt truncated due to length]", True

        # Keep everything before context
        before_context = prompt[:context_start]

        # Calculate available space for context
        before_tokens = len(before_context) // 4
        available_tokens = (
            self.MAX_TOKENS - before_tokens - 50
        )  # Reserve 50 for truncation notice
        available_chars = available_tokens * 4

        if available_chars <= 0:
            # Foundation blocks are already too long
            max_chars = self.MAX_TOKENS * 4
            return prompt[:max_chars] + "\n\n[Prompt truncated due to length]", True

        # Truncate context section
        context_section = prompt[context_start:]
        truncated_context = context_section[:available_chars]

        truncated_prompt = (
            before_context + truncated_context + "\n\n[Context truncated due to length]"
        )

        return truncated_prompt, True
