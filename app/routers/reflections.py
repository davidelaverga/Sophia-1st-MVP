"""
Reflection Cards API

Generates, stores, and exposes "Reflection Cards" - summaries of meaningful
conversation moments.

Endpoints:
- POST /api/reflections/run - Generate reflection card
- GET /api/reflections/latest - Get user's latest cards
- GET /api/reflections/{id} - Get specific card
"""

import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from app.deps import verify_api_key, limiter
from app.config import get_settings
from app.services.supabase import get_supabase
from app.services.memory import memory_manager

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/reflections", tags=["reflections"])


class ReflectionRequest(BaseModel):
    """Request to generate a reflection card"""
    conversation_id: str = Field(..., description="Conversation/session ID")
    user_id: str = Field(..., description="User ID")
    share_to_discord: bool = Field(default=False, description="Share to Discord #reflections")


class ReflectionCard(BaseModel):
    """Reflection card response"""
    id: str
    user_id: str
    conversation_id: str
    title: Optional[str]
    summary: str
    insight_tags: List[str]
    sophia_emotion: Dict[str, Any]
    user_emotion: Optional[Dict[str, Any]]
    shared: bool
    discord_message_id: Optional[str]
    created_at: str


class ReflectionListResponse(BaseModel):
    """List of reflection cards"""
    user_id: str
    reflections: List[ReflectionCard]


def _generate_reflection_helper(conversation_id: str) -> Dict[str, Any]:
    """
    Generate reflection using M3 Reflection Helper (placeholder).
    
    TODO: Replace with actual M3 Reflection Helper when available.
    For now, generates based on memory context.
    """
    
    # Get conversation context from memory
    context = memory_manager.get_session_memory(conversation_id)
    
    if not context or not context.turns:
        raise ValueError("No conversation data found for reflection")
    
    # Extract meaningful moments (simple heuristic for MVP)
    topics = context.topics if context.topics else ["general conversation"]
    last_emotions = {
        "user": context.user_tone_history[-1] if context.user_tone_history else "neutral",
        "sophia": context.sophia_tone_history[-1] if context.sophia_tone_history else "neutral"
    }
    
    # Generate title and summary (placeholder logic)
    title = f"Reflection on {', '.join(topics[:2])}"
    summary = f"We explored {', '.join(topics)}. The conversation felt {last_emotions['user']}."
    
    # Extract insight tags
    insight_tags = topics[:3] if topics else ["conversation"]
    
    # Sophia emotion from last turn
    sophia_emotion = {
        "label": last_emotions["sophia"],
        "confidence": 0.85
    }
    
    # User emotion from last turn
    user_emotion = {
        "label": last_emotions["user"],
        "confidence": 0.75
    }
    
    return {
        "title": title,
        "summary": summary,
        "insight_tags": insight_tags,
        "sophia_emotion": sophia_emotion,
        "user_emotion": user_emotion
    }


async def _post_to_discord_webhook(card: Dict[str, Any]) -> Optional[str]:
    """
    Post reflection card to Discord webhook.
    
    Returns Discord message ID if successful.
    """
    
    discord_webhook_url = getattr(settings, "DISCORD_REFLECTIONS_WEBHOOK", None)
    
    if not discord_webhook_url:
        logger.warning("Discord webhook not configured")
        return None
    
    try:
        import requests
        
        embed = {
            "title": card.get("title", "Reflection"),
            "description": card.get("summary", ""),
            "color": 5814783,  # Purple
            "fields": [
                {
                    "name": "Insights",
                    "value": ", ".join(card.get("insight_tags", [])),
                    "inline": True
                },
                {
                    "name": "Emotion",
                    "value": card.get("sophia_emotion", {}).get("label", "neutral"),
                    "inline": True
                }
            ],
            "footer": {"text": "Sophia AI Reflection"}
        }
        
        payload = {"embeds": [embed]}
        
        response = requests.post(discord_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        # Discord doesn't return message ID in webhook response
        # Would need Discord bot for that
        return "webhook_posted"
        
    except Exception as e:
        logger.error(f"Failed to post to Discord webhook: {e}")
        return None


@router.post("/run")
@limiter.limit(settings.API_RATE_LIMIT)
async def create_reflection(
    request: Request,
    body: ReflectionRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Generate and store a Reflection Card for a conversation.
    
    Flow:
    1. Retrieve conversation context from memory
    2. Call M3 Reflection Helper to generate reflection
    3. Store in reflection_cards table
    4. Optionally post to Discord
    """
    
    try:
        logger.info(f"[Reflection] Generating for conversation {body.conversation_id}")
        
        # Generate reflection
        reflection_data = _generate_reflection_helper(body.conversation_id)
        
        # Create reflection record
        reflection_id = str(uuid.uuid4())
        created_at = time.time()
        
        card = {
            "id": reflection_id,
            "user_id": body.user_id,
            "conversation_id": body.conversation_id,
            "title": reflection_data["title"],
            "summary": reflection_data["summary"],
            "insight_tags": reflection_data["insight_tags"],
            "sophia_emotion": reflection_data["sophia_emotion"],
            "user_emotion": reflection_data["user_emotion"],
            "shared": body.share_to_discord,
            "discord_message_id": None,
            "created_at": created_at
        }
        
        # Post to Discord if requested
        if body.share_to_discord:
            discord_msg_id = await _post_to_discord_webhook(card)
            card["discord_message_id"] = discord_msg_id
        
        # Store in Supabase
        supabase = get_supabase()
        try:
            supabase.table("reflection_cards").insert({
                "id": card["id"],
                "user_id": card["user_id"],
                "conversation_id": card["conversation_id"],
                "title": card["title"],
                "summary": card["summary"],
                "insight_tags": card["insight_tags"],
                "sophia_emotion": card["sophia_emotion"],
                "user_emotion": card["user_emotion"],
                "shared": card["shared"],
                "discord_message_id": card["discord_message_id"]
            }).execute()
            
            logger.info(f"[Reflection] Created card {reflection_id}")
        except Exception as e:
            logger.error(f"[Reflection] Failed to store in Supabase: {e}")
            # Continue anyway - return the card even if storage fails
        
        return ReflectionCard(**{
            **card,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created_at))
        })
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[Reflection] Failed to create: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create reflection")


@router.get("/latest")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_latest_reflections(
    request: Request,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=3, ge=1, le=10, description="Number of cards to return"),
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get user's latest reflection cards (newest first).
    """
    
    try:
        supabase = get_supabase()
        
        result = supabase.table("reflection_cards").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        reflections = []
        for row in result.data:
            reflections.append(ReflectionCard(
                id=row["id"],
                user_id=row["user_id"],
                conversation_id=row["conversation_id"],
                title=row.get("title"),
                summary=row["summary"],
                insight_tags=row.get("insight_tags", []),
                sophia_emotion=row.get("sophia_emotion", {}),
                user_emotion=row.get("user_emotion"),
                shared=row.get("shared", False),
                discord_message_id=row.get("discord_message_id"),
                created_at=row.get("created_at", "")
            ))
        
        return ReflectionListResponse(
            user_id=user_id,
            reflections=reflections
        )
        
    except Exception as e:
        logger.error(f"[Reflection] Failed to get latest: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reflections")


@router.get("/{reflection_id}")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_reflection(
    request: Request,
    reflection_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get a specific reflection card by ID.
    """
    
    try:
        supabase = get_supabase()
        
        result = supabase.table("reflection_cards").select("*").eq(
            "id", reflection_id
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Reflection not found")
        
        row = result.data[0]
        
        return ReflectionCard(
            id=row["id"],
            user_id=row["user_id"],
            conversation_id=row["conversation_id"],
            title=row.get("title"),
            summary=row["summary"],
            insight_tags=row.get("insight_tags", []),
            sophia_emotion=row.get("sophia_emotion", {}),
            user_emotion=row.get("user_emotion"),
            shared=row.get("shared", False),
            discord_message_id=row.get("discord_message_id"),
            created_at=row.get("created_at", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Reflection] Failed to get: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reflection")