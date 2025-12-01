"""SQLAlchemy engine and session helpers for Supabase Postgres access."""

from __future__ import annotations

import contextlib
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine(echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine bound to the Supabase connection string."""
    settings = get_settings()
    if not settings.SUPABASE_DB_DSN:
        raise RuntimeError("SUPABASE_DB_DSN not configured")

    engine = create_engine(
        settings.SUPABASE_DB_DSN,
        echo=echo,
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory backed by the Supabase engine."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)


@contextlib.contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for SQLAlchemy ORM usage."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
