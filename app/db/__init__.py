"""SQLAlchemy base metadata, models, and session utilities for the Sophia backend."""

from .base import Base

# Re-export models so consumers can import from app.db directly.
from . import models  # noqa: F401
from .session import get_engine, get_session_factory, session_scope  # noqa: F401

__all__ = ["Base", "models", "get_engine", "get_session_factory", "session_scope"]
