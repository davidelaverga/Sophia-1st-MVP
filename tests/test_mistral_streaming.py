import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services import mistral as mistral_service
import pytest


class _Event:
    """Minimal stand-in for Mistral's CompletionEvent."""

    def __init__(self, pieces):
        self.data = _Chunk(pieces)


class _Chunk:
    def __init__(self, pieces):
        self.choices = [_Choice(pieces)]


class _Choice:
    def __init__(self, pieces):
        self.delta = _Delta(pieces)


class _Delta:
    def __init__(self, pieces):
        self.content = pieces


class _DummyStream:
    """Simple iterable that mimics the SDK event stream."""

    def __init__(self, events):
        self._iterator = iter(events)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iterator)


class _DummyChat:
    def __init__(self, stream):
        self._stream = stream

    def stream(self, **_kwargs):
        return self._stream


class _DummyClient:
    def __init__(self, stream):
        self.chat = _DummyChat(stream)


def _completion_event(text):
    return _Event([_TextChunk(text)])


class _TextChunk:
    def __init__(self, text):
        self.text = text


def test_stream_generate_llm_reply_handles_completion_event(monkeypatch):
    """Ensure streaming yields text chunks instead of falling back."""
    events = [
        _completion_event("Hello"),
        _completion_event(" "),
        _completion_event("world"),
    ]
    dummy_stream = _DummyStream(events)
    dummy_client = _DummyClient(dummy_stream)
    monkeypatch.setattr(mistral_service, "_client", lambda: dummy_client)

    tokens = list(mistral_service.stream_generate_llm_reply("How are markets?"))

    assert tokens == ["Hello", " ", "world"]


def test_stream_generate_llm_reply_raises_when_cancel_requested(monkeypatch):
    """Cancellation callback should be honored between streamed chunks."""
    events = [
        _completion_event("Alpha"),
        _completion_event("Beta"),
    ]
    dummy_stream = _DummyStream(events)
    dummy_client = _DummyClient(dummy_stream)
    monkeypatch.setattr(mistral_service, "_client", lambda: dummy_client)

    call_counter = {"count": 0}

    def _cancel_check():
        call_counter["count"] += 1
        if call_counter["count"] >= 6:
            raise asyncio.CancelledError()

    stream = mistral_service.stream_generate_llm_reply(
        "Walk me through staking.", cancel_check=_cancel_check
    )

    assert next(stream) == "Alpha"
    with pytest.raises(asyncio.CancelledError):
        next(stream)
