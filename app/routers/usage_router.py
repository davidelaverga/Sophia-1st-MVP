"""
Usage Limits and Plans API

Endpoints for checking usage, viewing plans, and managing subscriptions.
"""

import logging
from typing import Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.deps import verify_api_key, limiter
from app.config import get_settings
from app.services.rate_limits import rate_limit_service
from app.services.plan_config import get_plan_info, get_all_plans, PLAN_LIMITS

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/usage", tags=["usage"])


class UsageLimitsResponse(BaseModel):
    """Current usage and limits for a user"""
    user_id: str
    plan_tier: str
    limits: Dict[str, int]
    daily_usage: Dict[str, int]
    monthly_reflections_used: int
    remaining: Dict[str, int]
    percentage_used: Dict[str, float]


class PlanInfoResponse(BaseModel):
    """Information about a specific plan"""
    tier: str
    display_name: str
    daily_voice_minutes: int
    daily_text_messages: int
    monthly_reflections: int
    price_display: str


@router.get("/limits")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_user_usage_limits(
    request: Request,
    user_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get current usage and limits for a user.
    
    Returns:
    - Current plan tier
    - Plan limits
    - Today's usage
    - Remaining quota
    - Percentage used
    
    Query Parameters:
    - user_id: User UUID
    """
    
    try:
        # Get user's plan
        plan_tier = rate_limit_service.get_user_plan_tier(user_id)
        limits = PLAN_LIMITS[plan_tier]
        
        # Get daily usage
        daily_usage = rate_limit_service.get_daily_usage(user_id)
        
        # Get monthly reflections
        monthly_reflections = rate_limit_service.get_monthly_reflection_count(user_id)
        
        # Calculate remaining
        remaining = {
            "voice_seconds": max(0, limits["daily_voice_seconds"] - daily_usage["voice_seconds"]),
            "text_messages": max(0, limits["daily_text_messages"] - daily_usage["text_messages"]),
            "reflections": max(0, limits["monthly_reflections"] - monthly_reflections),
        }
        
        # Calculate percentage used
        percentage_used = {
            "voice": round((daily_usage["voice_seconds"] / limits["daily_voice_seconds"]) * 100, 2),
            "text": round((daily_usage["text_messages"] / limits["daily_text_messages"]) * 100, 2),
            "reflections": round((monthly_reflections / limits["monthly_reflections"]) * 100, 2),
        }
        
        return UsageLimitsResponse(
            user_id=user_id,
            plan_tier=plan_tier,
            limits=limits,
            daily_usage={
                "voice_seconds": daily_usage["voice_seconds"],
                "text_messages": daily_usage["text_messages"],
            },
            monthly_reflections_used=monthly_reflections,
            remaining=remaining,
            percentage_used=percentage_used,
        )
        
    except Exception as e:
        logger.error(f"Failed to get usage limits: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage limits")


@router.get("/plans")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_available_plans(
    request: Request,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get information about all available plans.
    
    Returns list of plans with pricing and limits.
    """
    
    try:
        plans = get_all_plans()
        
        return {
            "plans": [
                {
                    "tier": plan.tier,
                    "display_name": plan.display_name,
                    "daily_voice_minutes": plan.daily_voice_minutes,
                    "daily_text_messages": plan.daily_text_messages,
                    "monthly_reflections": plan.monthly_reflections,
                    "price": plan.price,
                    "currency": plan.currency,
                    "interval": plan.interval,
                    "price_display": plan.price_display,
                }
                for plan in plans
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve plans")


@router.get("/plan/{tier}")
@limiter.limit(settings.API_RATE_LIMIT)
async def get_plan_details(
    request: Request,
    tier: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """
    Get detailed information about a specific plan.
    
    Path Parameters:
    - tier: Plan tier (FREE, SUPPORTER, FOUNDING_SUPPORTER)
    """
    
    if tier not in PLAN_LIMITS:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        plan = get_plan_info(tier)
        
        return {
            "tier": plan.tier,
            "display_name": plan.display_name,
            "daily_voice_minutes": plan.daily_voice_minutes,
            "daily_text_messages": plan.daily_text_messages,
            "monthly_reflections": plan.monthly_reflections,
            "price": plan.price,
            "currency": plan.currency,
            "interval": plan.interval,
            "price_display": plan.price_display,
        }
        
    except Exception as e:
        logger.error(f"Failed to get plan details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve plan details")