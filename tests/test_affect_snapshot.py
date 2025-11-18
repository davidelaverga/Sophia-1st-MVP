"""Unit tests for MemoryManager affect snapshot APIs (flash + redis backends)."""

import time

from app.services.memory import MemoryManager


class _FakeRedis:
    def __init__(self):
        self.storage = {}

    def setex(self, key, _ttl, value):
        self.storage[key] = value

    def get(self, key):
        return self.storage.get(key)


def _new_manager() -> MemoryManager:
    manager = MemoryManager()
    manager.redis_client = None  # Force flash backend for deterministic tests
    return manager


def test_affect_snapshot_flash_backend_roundtrip():
    manager = _new_manager()
    session_id = "flash-session"
    payload = {
        "emotion": "joy",
        "confidence": 0.84,
        "trend": "rising",
        "sentiment": "positive",
        "voice_signal_present": True,
    }

    manager.set_affect_snapshot(session_id, payload)
    snapshot = manager.get_affect_snapshot(session_id)
    assert snapshot["emotion"] == "joy"
    assert snapshot["voice_signal_present"] is True

    # Expire entry manually and ensure it is purged
    manager._affect_flash_store[session_id] = (snapshot, time.time() - 1)
    assert manager.get_affect_snapshot(session_id) is None


def test_affect_snapshot_redis_backend_roundtrip():
    manager = _new_manager()
    manager.redis_client = _FakeRedis()
    session_id = "redis-session"
    payload = {
        "emotion": "sad",
        "confidence": 0.42,
        "trend": "falling",
        "sentiment": "negative",
        "voice_signal_present": False,
    }

    manager.set_affect_snapshot(session_id, payload)
    assert manager._affect_flash_store[session_id][0]["emotion"] == "sad"

    # Clear flash store to force redis fetch
    manager._affect_flash_store.clear()
    snapshot = manager.get_affect_snapshot(session_id)
    assert snapshot["emotion"] == "sad"
    assert snapshot["trend"] == "falling"
