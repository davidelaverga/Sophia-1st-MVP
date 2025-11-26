"""
Phoenix emotion classification test endpoint.

Task #42841
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import verify_api_key
from app.emotion import PhoenixClient, PhoenixConfig, PhoenixResult
from app.config import get_settings

router = APIRouter(prefix="/api/phoenix", tags=["phoenix"])
logger = logging.getLogger("phoenix_test")


class EmotionClassifyRequest(BaseModel):
    """Request to classify emotion from text."""
    text: str = Field(..., min_length=1, description="User message text")
    prosody_context: Optional[str] = Field(
        None,
        description="Optional prosody analysis (e.g., 'pitch: high, pace: fast')"
    )


class EmotionClassifyResponse(BaseModel):
    """Response with emotion classification result."""
    label: str = Field(..., description="Detected emotion label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    safety_flag: bool = Field(..., description="Crisis intervention flag")
    source: str = Field(default="phoenix", description="Classification source")


@router.post("/classify", response_model=EmotionClassifyResponse)
async def classify_emotion(
    request: EmotionClassifyRequest,
    _token: str = Depends(verify_api_key)
) -> EmotionClassifyResponse:
    """
    Classify emotion from text using PhoenixClient with OpenAI.

    Returns emotion label, confidence, and safety flag for crisis detection.

    Example request:
    ```json
    {
        "text": "I'm really worried about the exam tomorrow",
        "prosody_context": "pitch: high, pace: fast"
    }
    ```

    Example response:
    ```json
    {
        "label": "anxious",
        "confidence": 0.87,
        "safety_flag": false,
        "source": "phoenix"
    }
    ```
    """
    settings = get_settings()

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )

    # Create Phoenix client
    config = PhoenixConfig(
        base_url="https://api.openai.com/v1",
        api_key=settings.OPENAI_API_KEY,
        timeout_seconds=12.0
    )

    try:
        async with PhoenixClient(config) as client:
            result: PhoenixResult = await client.classify(
                text=request.text,
                prosody_context=request.prosody_context
            )

            logger.info(
                "Phoenix classification: text=%s, label=%s, confidence=%.2f, safety=%s",
                request.text[:50],
                result.label,
                result.confidence,
                result.safety_flag
            )

            return EmotionClassifyResponse(
                label=result.label,
                confidence=result.confidence,
                safety_flag=result.safety_flag,
                source="phoenix"
            )

    except Exception as e:
        logger.error("Phoenix classification failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Emotion classification failed: {str(e)}"
        )


@router.get("/health")
async def health_check() -> dict:
    """Check if Phoenix endpoint is available and configured."""
    settings = get_settings()

    has_api_key = bool(settings.OPENAI_API_KEY)

    return {
        "status": "healthy" if has_api_key else "degraded",
        "openai_configured": has_api_key,
        "model": "gpt-4o-mini",
        "timeout_seconds": 12.0,
        "valid_emotions": [
            "joy", "excited", "sad", "anxious", "grief", "panic",
            "anger", "fearful", "calm", "neutral", "hopeful", "lonely"
        ]
    }
