"""
Payment Plans Configuration

Defines plan tiers and their limits for voice, text, and reflections.
"""

from typing import Dict, Literal
from dataclasses import dataclass

# Plan tier types
PlanTier = Literal["FREE", "SUPPORTER", "FOUNDING_SUPPORTER"]

# Plan limits configuration
PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "FREE": {
        "daily_voice_seconds": 600,      # 10 min/day
        "daily_text_messages": 40,       # 40 text turns/day
        "monthly_reflections": 4,        # 4 cards/month
    },
    "SUPPORTER": {
        "daily_voice_seconds": 3600,     # 60 min/day
        "daily_text_messages": 200,      # 200 text turns/day
        "monthly_reflections": 30,       # 30 cards/month
    },
    "FOUNDING_SUPPORTER": {
        "daily_voice_seconds": 7200,     # 120 min/day
        "daily_text_messages": 400,      # 400 text turns/day
        "monthly_reflections": 100,      # 100 cards/month
    },
}

# Human-readable plan names for display
PLAN_DISPLAY_NAMES: Dict[str, str] = {
    "FREE": "Free",
    "SUPPORTER": "Supporter",
    "FOUNDING_SUPPORTER": "Founding Supporter",
}

# Plan pricing (for display purposes)
PLAN_PRICING: Dict[str, Dict[str, any]] = {
    "FREE": {
        "price": 0,
        "currency": "USD",
        "interval": None,
    },
    "SUPPORTER": {
        "price": 9.99,
        "currency": "USD",
        "interval": "month",
    },
    "FOUNDING_SUPPORTER": {
        "price": 29.99,
        "currency": "USD",
        "interval": "month",
    },
}

# Friendly error messages for limit exceeded
LIMIT_EXCEEDED_MESSAGES: Dict[str, Dict[str, str]] = {
    "voice": {
        "title": "You've reached today's free voice limit 💜",
        "body": """Sophia is still in her early days. She's not a finished opera yet—she's an experiment in what an AI that truly tries to care about humans could become.

If you felt something with her and want to keep going today, you can become a Founding Supporter:
• Help us cover AI costs so Sophia can keep learning
• Unlock higher daily usage and more Reflection Cards
• Be part of the first group shaping who Sophia becomes

If money is tight or you're not sure yet, no pressure at all. You can always:
• Come back tomorrow for a fresh free daily limit ✨

Either way, thank you for helping Sophia grow."""
    },
    "text": {
        "title": "You've reached today's free text limit 💜",
        "body": """Sophia is still in her early days. She's not a finished opera yet—she's an experiment in what an AI that truly tries to care about humans could become.

If you felt something with her and want to keep going today, you can become a Founding Supporter:
• Help us cover AI costs so Sophia can keep learning
• Unlock higher daily usage and more Reflection Cards
• Be part of the first group shaping who Sophia becomes

If money is tight or you're not sure yet, no pressure at all. You can always:
• Come back tomorrow for a fresh free daily limit ✨

Either way, thank you for helping Sophia grow."""
    },
    "reflections": {
        "title": "You've reached this month's free reflection card limit 💜",
        "body": """Sophia is still in her early days. She's not a finished opera yet—she's an experiment in what an AI that truly tries to care about humans could become.

If you felt something with her and want more reflection cards this month, you can become a Founding Supporter:
• Help us cover AI costs so Sophia can keep learning
• Unlock up to 100 reflection cards per month
• Be part of the first group shaping who Sophia becomes

If money is tight or you're not sure yet, no pressure at all. You can always:
• Come back next month for a fresh free monthly limit ✨

Either way, thank you for helping Sophia grow."""
    }
}


@dataclass
class PlanInfo:
    """Plan information for display"""
    tier: str
    display_name: str
    daily_voice_seconds: int
    daily_text_messages: int
    monthly_reflections: int
    price: float
    currency: str
    interval: str | None
    
    @property
    def daily_voice_minutes(self) -> int:
        """Voice seconds converted to minutes"""
        return self.daily_voice_seconds // 60
    
    @property
    def price_display(self) -> str:
        """Formatted price string"""
        if self.price == 0:
            return "Free"
        if self.interval:
            return f"${self.price:.2f}/{self.interval}"
        return f"${self.price:.2f}"


def get_plan_info(tier: str) -> PlanInfo:
    """Get complete plan information"""
    limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["FREE"])
    pricing = PLAN_PRICING.get(tier, PLAN_PRICING["FREE"])
    
    return PlanInfo(
        tier=tier,
        display_name=PLAN_DISPLAY_NAMES.get(tier, "Unknown"),
        daily_voice_seconds=limits["daily_voice_seconds"],
        daily_text_messages=limits["daily_text_messages"],
        monthly_reflections=limits["monthly_reflections"],
        price=pricing["price"],
        currency=pricing["currency"],
        interval=pricing["interval"],
    )


def get_all_plans() -> list[PlanInfo]:
    """Get information for all available plans"""
    return [
        get_plan_info(tier) 
        for tier in ["FREE", "SUPPORTER", "FOUNDING_SUPPORTER"]
    ]