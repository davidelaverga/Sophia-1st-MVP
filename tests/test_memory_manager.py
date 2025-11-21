"""Tests for MemoryManager fallback when Redis is unavailable."""

import time
from unittest.mock import patch

from app.services.memory import ConversationTurn, MemoryManager


def _make_manager() -> MemoryManager:
    manager = MemoryManager()
    manager.redis_client = None
    manager._local_store.clear()
    manager._local_store_limit = 10
    manager._local_store_ttl = 3600
    return manager


def _turn(query: str, intent: str = "casual") -> ConversationTurn:
    return ConversationTurn(
        query=query,
        response="ack",
        user_emotion="neutral",
        sophia_emotion="neutral",
        intent=intent,
        timestamp=time.time(),
    )


def test_local_memory_used_when_redis_missing():
    manager = _make_manager()
    session_id = "session-local"

    manager.update_session_memory(
        session_id, _turn("Let's talk about staking", intent="defi_question")
    )
    manager.update_session_memory(
        session_id, _turn("Also yield farming today", intent="follow_up")
    )

    with patch("app.services.memory.get_supabase") as mock_supabase:
        context = manager.get_context_for_llm(session_id)

    mock_supabase.assert_not_called()
    assert context["conversation_turns"] == 2
    assert "staking" in context["last_topics"]
    assert context["recent_intents"] == ["defi_question", "follow_up"]
    assert context["recent_turns"][-1]["user"] == "Also yield farming today"
    assert context["recent_turns"][0]["sophia"] == "ack"


def test_local_memory_entries_expire_after_ttl():
    manager = _make_manager()
    manager._local_store_ttl = 1
    session_id = "session-expire"

    manager.update_session_memory(session_id, _turn("I like staking rewards"))

    stored_memory, _ = manager._local_store[session_id]
    manager._local_store[session_id] = (stored_memory, time.time() - 5)

    assert manager._get_local_memory(session_id) is None
    assert session_id not in manager._local_store
