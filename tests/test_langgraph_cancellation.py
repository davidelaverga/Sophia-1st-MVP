"""Tests ensuring LangGraph nodes honour cancellation requests before fallbacks."""

import asyncio

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain")

from app.langgraph_nodes import AudioIngestor


def test_audio_ingestor_whisper_fallback_honours_cancellation(monkeypatch):
    """When a turn is cancelled, the Whisper fallback should not run."""
    ingestor = AudioIngestor(use_voxtral_large=False)

    call_counter = {"count": 0}

    def cancel_check():
        call_counter["count"] += 1
        if call_counter["count"] >= 2:
            raise asyncio.CancelledError()

    state = {
        "session_id": "sess-cancel",
        "audio_bytes": b"RIFFdata",
        "fallback_used": {},
        "cancel_check": cancel_check,
    }

    def _transcribe_fail(*_args, **_kwargs):
        raise RuntimeError("primary STT failed")

    whisper_called = {"flag": False}

    def _fake_whisper(self, _state, _audio_bytes):
        whisper_called["flag"] = True
        return "fallback transcript"

    monkeypatch.setattr("app.langgraph_nodes.transcribe_audio_with_voxtral", _transcribe_fail)
    monkeypatch.setattr(AudioIngestor, "_whisper_fallback", _fake_whisper, raising=False)
    monkeypatch.setattr("app.langgraph_nodes.analyze_emotion_audio", lambda *_args, **_kwargs: None)

    with pytest.raises(asyncio.CancelledError):
        ingestor._legacy_audio_ingestion(state)

    assert not whisper_called["flag"], "Whisper fallback should not execute after cancellation"
