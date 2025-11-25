"""
Rate Limit Enforcement System

Checks and enforces usage limits for voice, text, and reflections.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from app.services.supabase import get_supabase
from app.services.plan_config import PLAN_LIMITS, LIMIT_EXCEEDED_MESSAGES

logger = logging.getLogger(__name__)


@dataclass
class LimitCheckResult:
    """Result of a limit check operation"""
    allowed: bool
    reason: Optional[str] = None  # 'voice', 'text', 'reflections'
    limit: Optional[int] = None
    used: Optional[int] = None
    plan_tier: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "limit": self.limit,
            "used": self.used,
            "plan_tier": self.plan_tier,
            "title": self.title,
            "body": self.body,
        }


class RateLimitService:
    """Service for managing user rate limits"""
    
    @staticmethod
    def get_user_plan_tier(user_id: str) -> str:
        """
        Get user's plan tier from database.
        Returns 'FREE' as default if user not found.
        """
        try:
            supabase = get_supabase()
            result = supabase.table("users").select("plan_tier").eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("plan_tier", "FREE")
            
            # User not found, return FREE
            return "FREE"
        except Exception as e:
            logger.error(f"Failed to get user plan tier: {e}")
            return "FREE"  # Safe default
    
    @staticmethod
    def get_daily_usage(user_id: str, usage_date: date = None) -> dict:
        """
        Get user's usage for a specific date.
        Returns dict with voice_seconds, text_messages, text_tokens.
        """
        if usage_date is None:
            usage_date = date.today()
        
        try:
            supabase = get_supabase()
            result = supabase.table("user_daily_usage").select(
                "voice_seconds, text_messages, text_tokens"
            ).eq("user_id", user_id).eq("usage_date", usage_date.isoformat()).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # No usage yet today
            return {
                "voice_seconds": 0,
                "text_messages": 0,
                "text_tokens": 0,
            }
        except Exception as e:
            logger.error(f"Failed to get daily usage: {e}")
            return {
                "voice_seconds": 0,
                "text_messages": 0,
                "text_tokens": 0,
            }
    
    @staticmethod
    def get_monthly_reflection_count(user_id: str) -> int:
        """
        Count reflections created this month.
        """
        try:
            supabase = get_supabase()
            
            # Get start of current month
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            result = supabase.table("reflection_cards").select(
                "id", count="exact"
            ).eq("user_id", user_id).gte(
                "created_at", month_start.isoformat()
            ).execute()
            
            return result.count or 0
        except Exception as e:
            logger.error(f"Failed to count monthly reflections: {e}")
            return 0
    
    @staticmethod
    def add_voice_usage(user_id: str, seconds: int) -> None:
        """
        Add voice usage for user.
        Uses Supabase function for atomic upsert.
        """
        try:
            supabase = get_supabase()
            today = date.today().isoformat()
            
            # Use the upsert function we created in SQL
            supabase.rpc(
                "upsert_user_daily_usage",
                {
                    "p_user_id": user_id,
                    "p_usage_date": today,
                    "p_voice_seconds": seconds,
                    "p_text_messages": 0,
                    "p_text_tokens": 0,
                }
            ).execute()
            
            logger.info(f"Added {seconds}s voice usage for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to add voice usage: {e}")
    
    @staticmethod
    def add_text_usage(user_id: str, messages: int = 1, tokens: int = 0) -> None:
        """
        Add text message usage for user.
        """
        try:
            supabase = get_supabase()
            today = date.today().isoformat()
            
            supabase.rpc(
                "upsert_user_daily_usage",
                {
                    "p_user_id": user_id,
                    "p_usage_date": today,
                    "p_voice_seconds": 0,
                    "p_text_messages": messages,
                    "p_text_tokens": tokens,
                }
            ).execute()
            
            logger.info(f"Added {messages} text message(s) for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to add text usage: {e}")
    
    @staticmethod
    def check_limits(
        user_id: str,
        additional_voice_sec: int = 0,
        additional_text_msgs: int = 0,
        additional_reflections: int = 0
    ) -> LimitCheckResult:
        """
        Check if user is within their plan limits.
        
        Args:
            user_id: User UUID
            additional_voice_sec: Voice seconds to add
            additional_text_msgs: Text messages to add
            additional_reflections: Reflections to add
        
        Returns:
            LimitCheckResult with allowed=True/False and metadata
        """
        # Get user's plan
        plan_tier = RateLimitService.get_user_plan_tier(user_id)
        limits = PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["FREE"])
        
        # Check voice limits
        if additional_voice_sec > 0:
            daily_usage = RateLimitService.get_daily_usage(user_id)
            current_voice = daily_usage["voice_seconds"]
            
            if current_voice + additional_voice_sec > limits["daily_voice_seconds"]:
                messages = LIMIT_EXCEEDED_MESSAGES["voice"]
                return LimitCheckResult(
                    allowed=False,
                    reason="voice",
                    limit=limits["daily_voice_seconds"],
                    used=current_voice,
                    plan_tier=plan_tier,
                    title=messages["title"],
                    body=messages["body"],
                )
        
        # Check text limits
        if additional_text_msgs > 0:
            daily_usage = RateLimitService.get_daily_usage(user_id)
            current_text = daily_usage["text_messages"]
            
            if current_text + additional_text_msgs > limits["daily_text_messages"]:
                messages = LIMIT_EXCEEDED_MESSAGES["text"]
                return LimitCheckResult(
                    allowed=False,
                    reason="text",
                    limit=limits["daily_text_messages"],
                    used=current_text,
                    plan_tier=plan_tier,
                    title=messages["title"],
                    body=messages["body"],
                )
        
        # Check reflection limits
        if additional_reflections > 0:
            current_reflections = RateLimitService.get_monthly_reflection_count(user_id)
            
            if current_reflections + additional_reflections > limits["monthly_reflections"]:
                messages = LIMIT_EXCEEDED_MESSAGES["reflections"]
                return LimitCheckResult(
                    allowed=False,
                    reason="reflections",
                    limit=limits["monthly_reflections"],
                    used=current_reflections,
                    plan_tier=plan_tier,
                    title=messages["title"],
                    body=messages["body"],
                )
        
        # All checks passed
        return LimitCheckResult(allowed=True, plan_tier=plan_tier)


# Singleton instance
rate_limit_service = RateLimitService()