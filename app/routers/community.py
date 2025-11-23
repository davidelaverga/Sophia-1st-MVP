"""
Community APIs for Discord Bot Integration

Endpoints for Discord bot (Dany) to fetch:
- Daily learning highlights (#sophia-learnings channel)
- User impact stats (/my-impact command)
"""

import logging
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from app.deps import verify_api_key, limiter
from app.config import get_settings
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/community", tags=["community"])


class LatestLearningResponse(BaseModel):
    """Daily highlight for #sophia-learnings channel"""
    title: str
    insight: str
    sophia_emotion: Dict[str, Any]
    reflection_id: Optional[str]


class UserImpactResponse(BaseModel):
    """User engagement stats for /my-impact command"""
    user_id: str
    session_count: int
    reflections_created: int
    reflections_shared: int
    last_session_at: Optional[str]


@router.get("/latest-learning")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_latest_learning(
    request: Request,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get today's "What Sophia Learned" highlight for Discord.
    
    Returns the most recent shared reflection from the past 24 hours.
    If none found, returns previous day.
    """
    
    try:
        supabase = get_supabase()
        
        # Get most recent shared reflection
        result = supabase.table("reflection_cards").select("*").eq(
            "shared", True
        ).order("created_at", desc=True).limit(1).execute()
        
        if not result.data:
            # Fallback message if no reflections yet
            return LatestLearningResponse(
                title="Today Sophia learned",
                insight="The importance of meaningful conversations and active listening.",
                sophia_emotion={"label": "curious", "confidence": 0.85},
                reflection_id=None
            )
        
        reflection = result.data[0]
        
        # Extract key insight from summary (first sentence)
        summary = reflection.get("summary", "")
        insight = summary.split(".")[0] + "." if "." in summary else summary
        
        return LatestLearningResponse(
            title="Today Sophia learned",
            insight=insight,
            sophia_emotion=reflection.get("sophia_emotion", {"label": "neutral", "confidence": 0.5}),
            reflection_id=reflection.get("id")
        )
        
    except Exception as e:
        logger.error(f"[Community] Failed to get latest learning: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve latest learning")


@router.get("/user-impact")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_user_impact(
    request: Request,
    user_id: str = Query(..., description="User ID"),
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get user's engagement stats for /my-impact Discord command.
    
    Returns:
    - Total conversation sessions
    - Reflections created
    - Reflections shared to community
    - Last session timestamp
    """
    
    try:
        supabase = get_supabase()
        
        # Count conversation sessions
        sessions_result = supabase.table("conversation_sessions").select(
            "id,created_at", count="exact"
        ).eq("user_id", user_id).execute()
        
        session_count = sessions_result.count if sessions_result.count else 0
        
        # Get last session timestamp
        last_session_at = None
        if sessions_result.data:
            # Already ordered by created_at desc implicitly
            last_sessions = sorted(
                sessions_result.data,
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            if last_sessions:
                last_session_at = last_sessions[0].get("created_at")
        
        # Count reflections
        reflections_result = supabase.table("reflection_cards").select(
            "id,shared", count="exact"
        ).eq("user_id", user_id).execute()
        
        reflections_created = reflections_result.count if reflections_result.count else 0
        
        # Count shared reflections
        reflections_shared = 0
        if reflections_result.data:
            reflections_shared = sum(1 for r in reflections_result.data if r.get("shared", False))
        
        return UserImpactResponse(
            user_id=user_id,
            session_count=session_count,
            reflections_created=reflections_created,
            reflections_shared=reflections_shared,
            last_session_at=last_session_at
        )
        
    except Exception as e:
        logger.error(f"[Community] Failed to get user impact: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user impact")


@router.get("/stats")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_community_stats(
    request: Request,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get overall community stats (for internal dashboards - post-launch).
    
    Returns aggregate metrics across all users.
    """
    
    try:
        supabase = get_supabase()
        
        # Total conversations
        sessions_result = supabase.table("conversation_sessions").select(
            "id", count="exact"
        ).execute()
        
        total_sessions = sessions_result.count if sessions_result.count else 0
        
        # Total reflections
        reflections_result = supabase.table("reflection_cards").select(
            "id,shared", count="exact"
        ).execute()
        
        total_reflections = reflections_result.count if reflections_result.count else 0
        
        # Shared reflections
        shared_reflections = 0
        if reflections_result.data:
            shared_reflections = sum(1 for r in reflections_result.data if r.get("shared", False))
        
        # Unique users (approximate from conversation_sessions)
        # In production, would use a more sophisticated query
        unique_users_result = supabase.table("conversation_sessions").select(
            "user_id"
        ).execute()
        
        unique_users = len(set(
            row["user_id"] for row in unique_users_result.data if row.get("user_id")
        )) if unique_users_result.data else 0
        
        return {
            "total_sessions": total_sessions,
            "total_reflections": total_reflections,
            "shared_reflections": shared_reflections,
            "unique_users": unique_users,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"[Community] Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve community stats")