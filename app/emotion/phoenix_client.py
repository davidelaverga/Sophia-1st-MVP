"""
PhoenixClient - Emotion classification wrapper using OpenAI API

Task #42841: Implement PhoenixClient wrapper with OpenAI support instead of Google API
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("phoenix_client")


@dataclass
class PhoenixConfig:
    """
    Configuration for PhoenixClient.

    Attributes:
        base_url: OpenAI API endpoint (e.g., "https://api.openai.com/v1")
        api_key: OpenAI API authentication token
        timeout_seconds: Hard timeout cap for API requests (default: 12s)
    """
    base_url: str
    api_key: str
    timeout_seconds: float = 12.0


@dataclass
class PhoenixResult:
    """
    Result from Phoenix emotion classification.

    Attributes:
        label: Detected emotion label (e.g., "anxious", "joy", "neutral")
        confidence: Confidence score between 0.0 and 1.0
        safety_flag: Boolean indicating if crisis intervention is needed
        raw: Raw response data from the API for debugging
    """
    label: str
    confidence: float
    safety_flag: bool
    raw: Dict[str, Any]


class PhoenixClient:
    """
    Async client for emotion classification using OpenAI API.

    Uses custom Sophia emotion prompt from prompts/sophia_phoenix_emotion_prompt.md
    instead of generic Phoenix prompts.

    Task #42841
    """

    # Valid emotion labels from Sophia emotion rails
    VALID_EMOTIONS = {
        "joy", "excited", "sad", "anxious", "grief", "panic",
        "anger", "fearful", "calm", "neutral", "hopeful", "lonely"
    }

    # Neutral fallback for errors/timeouts
    NEUTRAL_FALLBACK = PhoenixResult(
        label="neutral",
        confidence=0.3,
        safety_flag=False,
        raw={"fallback": True, "reason": "error_or_timeout"}
    )

    def __init__(self, config: PhoenixConfig):
        """
        Initialize PhoenixClient with configuration.

        Args:
            config: PhoenixConfig instance with API settings
        """
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
        )
        self.prompt_template = self._load_emotion_prompt()
        logger.info(
            "PhoenixClient initialized with base_url=%s, timeout=%ss",
            config.base_url,
            config.timeout_seconds
        )

    def _load_emotion_prompt(self) -> str:
        """
        Load custom Sophia emotion prompt from file.

        Returns:
            Prompt template string from sophia_phoenix_emotion_prompt.md
        """
        prompt_path = Path(__file__).parents[2] / "prompts" / "sophia_phoenix_emotion_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read()
            logger.info("Loaded custom Sophia emotion prompt from %s", prompt_path)
            return prompt
        except Exception as exc:
            logger.warning(
                "Failed to load custom emotion prompt from %s: %s. Using fallback.",
                prompt_path,
                exc
            )
            # Fallback inline prompt if file not found
            return """You are an expert emotion classifier. Classify the user's emotion from their message.
Valid emotions: joy, excited, sad, anxious, grief, panic, anger, fearful, calm, neutral, hopeful, lonely.
Return JSON with: label (emotion), confidence (0.0-1.0), safety_flag (boolean for crisis detection)."""

    async def classify(
        self,
        text: str,
        prosody_context: Optional[str] = None
    ) -> PhoenixResult:
        """
        Classify emotion from text and optional prosody context.

        Args:
            text: User message text to classify
            prosody_context: Optional prosody analysis (pitch, energy, pace)

        Returns:
            PhoenixResult with label, confidence, safety_flag, and raw response
            On error/timeout: Returns neutral fallback (label="neutral", confidence=0.3)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to classify(), returning neutral")
            return self.NEUTRAL_FALLBACK

        try:
            # Build payload using custom prompt
            payload = self._build_payload(text, prosody_context)

            # Make API request
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            # Parse response
            result = self._parse_response(response.json())

            logger.info(
                "Phoenix classification successful: label=%s, confidence=%.2f, safety_flag=%s",
                result.label,
                result.confidence,
                result.safety_flag
            )
            return result

        except httpx.TimeoutException:
            logger.warning(
                "Phoenix API timeout after %.1fs for text: %s",
                self.config.timeout_seconds,
                text[:100]
            )
            return self.NEUTRAL_FALLBACK

        except Exception as exc:
            logger.warning(
                "Phoenix classification error: %s. Returning neutral fallback. Text: %s",
                exc,
                text[:100]
            )
            return self.NEUTRAL_FALLBACK

    def _build_payload(self, text: str, prosody_context: Optional[str]) -> Dict[str, Any]:
        """
        Build OpenAI API payload with custom Sophia emotion prompt.

        Args:
            text: User message text
            prosody_context: Optional prosody analysis

        Returns:
            API request payload dict
        """
        # Construct user input with optional prosody context
        user_input = f"**text**: {text}"
        if prosody_context:
            user_input += f"\n**additional_context**: {prosody_context}"

        # Build messages for chat completion
        # Note: When using response_format json_object, the system message MUST instruct to output JSON
        system_message = (
            self.prompt_template +
            "\n\nIMPORTANT: You MUST respond with valid JSON in this exact format:\n"
            '{"label": "emotion_name", "confidence": 0.85, "safety_flag": false}\n'
            "Do not include any other text, only the JSON object."
        )

        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": user_input
            }
        ]

        # OpenAI API payload
        return {
            "model": "gpt-4o-mini",  # Fast and cost-effective model for classification
            "messages": messages,
            "temperature": 0.1,  # Low temperature for consistent classification
            "response_format": {"type": "json_object"},  # Force JSON response
            "max_tokens": 150
        }

    def _parse_response(self, response_data: Dict[str, Any]) -> PhoenixResult:
        """
        Parse OpenAI API response into PhoenixResult.

        Args:
            response_data: Raw API response JSON

        Returns:
            Parsed PhoenixResult
        """
        try:
            # Extract content from OpenAI response
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Extract fields
            label = str(parsed.get("label", "neutral")).strip().lower()
            confidence = float(parsed.get("confidence", 0.5))
            safety_flag = bool(parsed.get("safety_flag", False))

            # Validate emotion label
            if label not in self.VALID_EMOTIONS:
                logger.warning(
                    "Invalid emotion label '%s' from API, defaulting to neutral",
                    label
                )
                label = "neutral"
                confidence = max(0.3, confidence * 0.5)  # Reduce confidence

            # Clamp confidence to [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))

            return PhoenixResult(
                label=label,
                confidence=confidence,
                safety_flag=safety_flag,
                raw=response_data
            )

        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse Phoenix response: %s", exc)
            return self.NEUTRAL_FALLBACK

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
