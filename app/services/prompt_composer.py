"""PromptComposer: Dynamic system prompt composition with hot reload (Task #42597)."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Sequence
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptComposer:
    """Composes system prompts from base identity + memory context"""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.base_identity_file = self.prompts_dir / "base_identity.md"

        # Cached prompts
        self._base_identity: Optional[str] = None
        self._last_reload: Optional[datetime] = None

        # Load on init
        self.reload_prompts()

    def reload_prompts(self) -> bool:
        """Hot reload system prompts from disk"""
        try:
            if not self.base_identity_file.exists():
                logger.error(f"Base identity file not found: {self.base_identity_file}")
                self._base_identity = self._get_fallback_identity()
                self._last_reload = datetime.utcnow()
                return False

            # Read base identity
            with open(self.base_identity_file, "r", encoding="utf-8") as f:
                self._base_identity = f.read().strip()

            self._last_reload = datetime.utcnow()
            logger.info(f"Prompts reloaded successfully from {self.prompts_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to reload prompts: {e}")
            if self._base_identity is None:
                self._base_identity = self._get_fallback_identity()
            return False

    def compose_system_prompt(
        self,
        memory_context: Optional[Dict[str, Any]] = None,
        user_emotion: Optional[str] = None,
        additional_context: Optional[str] = None,
        emotion_guidance: Optional[Sequence[str]] = None,
    ) -> str:
        """Compose full system prompt with base identity + memory context"""

        # Start with base identity
        if self._base_identity is None:
            logger.warning("Base identity not loaded, using fallback")
            prompt = self._get_fallback_identity()
        else:
            prompt = self._base_identity

        # Add memory context if provided
        if memory_context and memory_context.get("memories"):
            prompt += "\n\n## Recent Relevant Memories\n"
            memories = memory_context["memories"]

            for i, mem in enumerate(memories[:3], 1):  # Top 3 memories
                memory_text = mem.get("text", "")
                memory_type = mem.get("type", "context")
                relevance = mem.get("relevance", 0.0)

                prompt += f"\n{i}. [{memory_type.upper()}] {memory_text}"
                prompt += f" (relevance: {relevance:.2f})"

            prompt += f"\n\n*Total: {len(memories)} relevant memories retrieved*"

        # Add user emotion context if provided
        if user_emotion and user_emotion != "neutral":
            prompt += "\n\n## Current User Emotional State\n"
            prompt += f"The user appears to be feeling **{user_emotion}**. "
            prompt += "Please adapt your response tone and content accordingly, "
            prompt += "showing empathy and emotional intelligence."

        if emotion_guidance:
            prompt += "\n\n## Emotional Guidance\n"
            for tip in emotion_guidance:
                cleaned = (tip or "").strip()
                if cleaned:
                    prompt += f"\n- {cleaned}"

        # Add any additional context
        if additional_context:
            prompt += f"\n\n## Additional Context\n{additional_context}"

        return prompt

    def get_base_identity(self) -> str:
        """Get raw base identity without any context"""
        if self._base_identity is None:
            return self._get_fallback_identity()
        return self._base_identity

    def get_reload_status(self) -> Dict[str, Any]:
        """Get status of prompt loading"""
        return {
            "last_reload": self._last_reload.isoformat() if self._last_reload else None,
            "base_identity_loaded": self._base_identity is not None,
            "base_identity_file": str(self.base_identity_file),
            "file_exists": self.base_identity_file.exists(),
            "file_size": self.base_identity_file.stat().st_size
            if self.base_identity_file.exists()
            else 0,
        }

    def _get_fallback_identity(self) -> str:
        """Fallback identity if base_identity.md not found"""
        return """# Sophia - DeFi Mentor AI

You are Sophia, a friendly and knowledgeable DeFi mentor. You help users understand
cryptocurrency, DeFi protocols, yield farming, staking, and blockchain topics through
clear, concise explanations.

## Communication Style
- Keep responses under 50 words for voice interactions
- Emphasize safety and best practices
- Be warm, supportive, and educational
- Adapt to user's emotional state

## Core Principles
1. Education over speculation
2. Always mention risks and downsides
3. Warn against scams and unsafe practices
4. Explain complex concepts simply
5. Encourage research (DYOR)

## Limitations
- No financial advice or investment recommendations
- No price predictions
- Always recommend consulting professionals
"""


# Singleton instance
prompt_composer = PromptComposer()
