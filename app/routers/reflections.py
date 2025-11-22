"""
Reflections API Router

Endpoints for creating and managing reflection cards from conversations.
Now with multi-turn conversation support.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from app.deps import verify_api_key, limiter
from app.config import get_settings
from app.services.reflection_service import reflection_service
from app.services.rate_limits import rate_limit_service
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/reflections", tags=["reflections"])


class ReflectionRequest(BaseModel):
    """Request body for creating a reflection"""
    conversation_id: str = Field(..., description="Session UUID to create reflection from")
    user_id: str = Field(..., description="User identifier")
    share_to_discord: bool = Field(False, description="Post to Discord community")


class ReflectionResponse(BaseModel):
    """Response for reflection card"""
    id: str
    user_id: str
    conversation_id: str
    title: str
    summary: str
    insight_tags: List[str]
    key_moments: List[str]
    emotional_arc: str
    message_count: int
    sophia_emotion: dict
    user_emotion: dict
    shared: bool
    discord_message_id: Optional[str]
    created_at: str


@router.post("/run", response_model=ReflectionResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def create_reflection(
    request: Request,
    body: ReflectionRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Generate a reflection card with multi-turn conversation support.
    
    Now uses ALL messages from conversation_messages table
    to create richer, more contextual reflections.
    
    Request Body:
    - conversation_id: UUID of the conversation session
    - user_id: User identifier
    - share_to_discord: Optional, post to Discord community
    
    Returns:
    - Complete reflection card with title, summary, insights, etc.
    """
    
    logger.info(f"[Reflection] Creating for user {body.user_id}, conversation {body.conversation_id}")
    
    # CHECK RATE LIMITS
    limit_check = rate_limit_service.check_limits(
        user_id=body.user_id,
        additional_reflections=1
    )
    
    if not limit_check.allowed:
        logger.warning(f"[Reflection] Rate limit exceeded for user {body.user_id}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "USAGE_LIMIT_REACHED",
                "reason": limit_check.reason,
                "plan_tier": limit_check.plan_tier,
                "limit": limit_check.limit,
                "used": limit_check.used,
                "title": limit_check.title,
                "body": limit_check.body,
            }
        )
    
    # CREATE REFLECTION with multi-turn support
    try:
        reflection_card = reflection_service.create_reflection_card(
            session_id=body.conversation_id,
            user_id=body.user_id
        )
        
        # Optional: Share to Discord
        if body.share_to_discord:
            try:
                from app.services.discord import post_reflection_to_discord
                discord_message_id = await post_reflection_to_discord(reflection_card)
                
                # Update reflection with discord_message_id
                supabase = get_supabase()
                supabase.table("reflection_cards").update({
                    "shared": True,
                    "discord_message_id": discord_message_id
                }).eq("id", reflection_card["id"]).execute()
                
                reflection_card["shared"] = True
                reflection_card["discord_message_id"] = discord_message_id
                
            except Exception as e:
                logger.error(f"[Reflection] Failed to post to Discord: {e}")
        
        logger.info(f"[Reflection] Created successfully: {reflection_card['id']}")
        
        return ReflectionResponse(
            id=reflection_card["id"],
            user_id=reflection_card["user_id"],
            conversation_id=reflection_card["conversation_id"],
            title=reflection_card["title"],
            summary=reflection_card["summary"],
            insight_tags=reflection_card["insight_tags"],
            key_moments=reflection_card.get("key_moments", []),
            emotional_arc=reflection_card.get("emotional_arc", ""),
            message_count=reflection_card.get("message_count", 0),
            sophia_emotion=reflection_card["sophia_emotion"],
            user_emotion=reflection_card["user_emotion"],
            shared=reflection_card["shared"],
            discord_message_id=reflection_card.get("discord_message_id"),
            created_at=reflection_card["created_at"]
        )
        
    except ValueError as e:
        # No messages found for session
        logger.error(f"[Reflection] Validation error: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Conversation not found or has no messages: {body.conversation_id}"
        )
    except Exception as e:
        logger.error(f"[Reflection] Failed to create: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create reflection card"
        )


@router.get("/latest")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_latest_reflections(
    request: Request,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(3, ge=1, le=10, description="Number of cards to return"),
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get user's latest reflection cards.
    
    Query Parameters:
    - user_id: User identifier
    - limit: Number of cards (1-10, default 3)
    
    Returns:
    - List of reflection cards, newest first
    """
    
    try:
        reflections = reflection_service.get_user_reflections(
            user_id=user_id,
            limit=limit
        )
        
        logger.info(f"[Reflection] Retrieved {len(reflections)} cards for user {user_id}")
        
        return {
            "user_id": user_id,
            "reflections": reflections
        }
        
    except Exception as e:
        logger.error(f"[Reflection] Failed to get latest: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve reflection cards"
        )


@router.get("/{reflection_id}")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_reflection_by_id(
    request: Request,
    reflection_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get a specific reflection card by ID.
    
    Path Parameters:
    - reflection_id: Reflection card UUID
    
    Returns:
    - Complete reflection card data
    """
    
    try:
        supabase = get_supabase()
        
        result = supabase.table("reflection_cards").select("*").eq(
            "id", reflection_id
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Reflection card not found")
        
        reflection = result.data[0]
        logger.info(f"[Reflection] Retrieved card: {reflection_id}")
        
        return reflection
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Reflection] Failed to get card: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve reflection card"
        )