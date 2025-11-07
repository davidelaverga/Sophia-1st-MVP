"""Tests for the per-session turn manager that serializes voice/chat turns."""

import asyncio

import pytest

from app.services.session_manager import SessionTurnManager, TurnInProgressError


def test_start_turn_blocks_parallel_when_cancellation_disabled():
    """Attempting a second turn without cancellation should raise immediately."""
    async def _run():
        manager = SessionTurnManager()
        first = await manager.start_turn("sess-123", cancel_existing=False)
        with pytest.raises(TurnInProgressError):
            await manager.start_turn("sess-123", cancel_existing=False)
        await manager.finish_turn(first.turn_id)

    asyncio.run(_run())


def test_start_turn_requests_cancel_and_waits_for_completion():
    """Default behaviour cancels the active turn and waits for it to finish before proceeding."""
    async def _run():
        manager = SessionTurnManager()
        first = await manager.start_turn("alpha-session")

        # Second requester should trigger cancellation and wait.
        follow_up = asyncio.create_task(manager.start_turn("alpha-session"))
        await asyncio.sleep(0)
        assert first.cancel_requested

        # Complete the first turn so the waiter can proceed.
        await manager.finish_turn(first.turn_id)
        second = await asyncio.wait_for(follow_up, timeout=1)

        assert second.turn_id != first.turn_id
        await manager.finish_turn(second.turn_id)

    asyncio.run(_run())


def test_request_cancel_triggers_raise_if_cancelled():
    """Explicit cancellation should cause raise_if_cancelled to surface CancelledError."""
    async def _run():
        manager = SessionTurnManager()
        state = await manager.start_turn("beta-session")
        manager.request_cancel(session_id="beta-session")

        with pytest.raises(asyncio.CancelledError):
            manager.raise_if_cancelled(state.turn_id)

        await manager.finish_turn(state.turn_id, status="cancelled")

    asyncio.run(_run())
