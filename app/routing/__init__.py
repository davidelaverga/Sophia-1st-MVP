"""Routing module for Sophia's conversational AI.

This module handles skill-based routing of conversations to specialized handlers.
"""

from app.routing.skills import SkillId, SkillRouteResult

__all__ = ["SkillId", "SkillRouteResult"]
