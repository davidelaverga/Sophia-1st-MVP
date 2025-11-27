import time

from app.services import memory
from app.services.memory import ConversationTurn, SessionMemory


def _build_manager(monkeypatch):
    # Force in-memory mode to avoid external Redis dependency
    monkeypatch.setattr(memory.MemoryManager, "_init_redis", lambda self: None)
    return memory.MemoryManager()


def _sample_turn(ts: float, intent: str = "intent"):
    return ConversationTurn(
        query="hi",
        response="hello",
        user_emotion="neutral",
        sophia_emotion="warm",
        intent=intent,
        timestamp=ts,
    )


def test_affect_snapshot_local_cache_and_expiry(monkeypatch):
    manager = _build_manager(monkeypatch)
    manager._affect_ttl_seconds = 1

    payload = {
        "emotion": "happy",
        "confidence": 0.9,
        "trend": "up",
        "sentiment": "positive",
        "voice_signal_present": True,
    }
    manager.set_affect_snapshot("session-1", payload)
    snapshot = manager.get_affect_snapshot("session-1")
    assert snapshot
    assert snapshot["emotion"] == "happy"

    # Simulate expiry in flash store
    manager._affect_flash_store["session-1"] = (snapshot, time.time() - 5)
    assert manager._get_local_affect("session-1") is None


def test_get_context_for_llm_uses_recent_turns(monkeypatch):
    manager = _build_manager(monkeypatch)
    turns = [_sample_turn(1.0, intent="greeting"), _sample_turn(2.0, intent="info")]
    memory_obj = SessionMemory(
        session_id="session-ctx",
        turns=turns,
        topics=["staking", "trading"],
        user_tone_history=["neutral", "sad"],
        sophia_tone_history=["warm", "warm"],
        created_at=0.0,
        updated_at=0.0,
    )
    manager._set_local_memory("session-ctx", memory_obj)

    context = manager.get_context_for_llm("session-ctx")
    assert context["last_topics"] == ["staking", "trading"]
    assert context["conversation_turns"] == len(turns)
    assert context["recent_intents"] == ["greeting", "info"]
    assert context["recent_turns"][0]["user"] == "hi"


def test_prune_local_store_respects_limit(monkeypatch):
    manager = _build_manager(monkeypatch)
    manager._local_store_limit = 2
    now = time.time()
    mem_a = SessionMemory("a", [], [], [], [], now, now)
    mem_b = SessionMemory("b", [], [], [], [], now, now)
    mem_c = SessionMemory("c", [], [], [], [], now, now)
    manager._local_store = {
        "a": (mem_a, now + 5),
        "b": (mem_b, now + 10),
        "c": (mem_c, now + 15),
    }

    manager._prune_local_store()
    assert len(manager._local_store) == 2
    # The earliest expiring entry should be pruned
    assert "a" not in manager._local_store
