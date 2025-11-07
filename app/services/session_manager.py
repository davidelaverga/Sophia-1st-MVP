"""Utilities for coordinating per-session turn state to avoid overlapping replies."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


logger = logging.getLogger("sophia-backend")

TurnStatus = Literal[
    "initializing",
    "streaming",
    "synthesizing",
    "cancelling",
    "completed",
    "cancelled",
    "failed",
]


class TurnInProgressError(RuntimeError):
    """Raised when a new turn is requested while another is still active."""

    def __init__(self, session_id: str):
        super().__init__(f"Session {session_id} already has an active turn")
        self.session_id = session_id


@dataclass
class TurnState:
    """Lightweight container tracking the lifecycle of a single response turn."""

    session_id: str
    turn_id: str
    status: TurnStatus = "initializing"
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    cancel_requested: bool = False
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    _done_event: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)

    def set_status(self, status: TurnStatus) -> None:
        """Update the current lifecycle status."""
        self.status = status
        self.updated_at = time.time()

    def request_cancel(self) -> None:
        """Mark that the caller would like this turn to stop as soon as possible."""
        if not self.cancel_requested:
            logger.info("Turn %s (session %s) cancellation requested", self.turn_id, self.session_id)
        self.cancel_requested = True
        self.updated_at = time.time()

    def mark_done(self, status: TurnStatus, error: Optional[str] = None) -> None:
        """Signal that the turn has reached a terminal state."""
        if status not in {"completed", "cancelled", "failed"}:
            raise ValueError(f"Invalid terminal status: {status}")
        self.status = status
        self.error = error
        self.updated_at = time.time()
        self._done_event.set()

    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Await completion of this turn, returning True when finished."""
        try:
            await asyncio.wait_for(self._done_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


class SessionTurnManager:
    """Serialises per-session turns so that at most one response is active."""

    def __init__(self):
        self._state_lock = asyncio.Lock()
        self._active_by_session: Dict[str, TurnState] = {}
        self._turn_index: Dict[str, TurnState] = {}

    async def start_turn(
        self,
        session_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        cancel_existing: bool = True,
        wait_for_cancel: bool = True,
        cancel_timeout: float = 5.0,
    ) -> TurnState:
        """Create a new turn for the given session, cancelling any active one if requested."""
        existing_state: Optional[TurnState] = None

        while True:
            async with self._state_lock:
                existing_state = self._active_by_session.get(session_id)
                if existing_state is None:
                    turn_id = uuid.uuid4().hex
                    state = TurnState(session_id=session_id, turn_id=turn_id)
                    if metadata:
                        state.context.update(metadata)
                    self._active_by_session[session_id] = state
                    self._turn_index[turn_id] = state
                    logger.info("Started new turn %s for session %s", turn_id, session_id)
                    return state

                if not cancel_existing:
                    logger.warning(
                        "Attempted to start turn for session %s while another turn %s is active",
                        session_id,
                        existing_state.turn_id,
                    )
                    raise TurnInProgressError(session_id)

                if not existing_state.cancel_requested:
                    existing_state.request_cancel()
                    existing_state.set_status("cancelling")

            # Outside lock: wait for existing turn to finish.
            if not wait_for_cancel:
                raise TurnInProgressError(session_id)

            finished = await existing_state.wait_for_completion(timeout=cancel_timeout)
            if not finished:
                logger.warning(
                    "Timed out waiting for session %s turn %s to finish; retrying",
                    session_id,
                    existing_state.turn_id,
                )
            else:
                logger.info(
                    "Previous turn %s for session %s finished with status %s; continuing",
                    existing_state.turn_id,
                    session_id,
                    existing_state.status,
                )

    async def finish_turn(
        self,
        turn_id: str,
        *,
        status: TurnStatus = "completed",
        error: Optional[str] = None,
    ) -> None:
        """Mark a turn as completed and release its session slot."""
        async with self._state_lock:
            state = self._turn_index.get(turn_id)
            if state is None:
                logger.debug("finish_turn called for unknown turn %s", turn_id)
                return
            state.mark_done(status, error)
            self._turn_index.pop(turn_id, None)
            self._active_by_session.pop(state.session_id, None)
            logger.info(
                "Turn %s for session %s finished with status %s",
                turn_id,
                state.session_id,
                status,
            )

    def get_turn(self, turn_id: str) -> Optional[TurnState]:
        """Return the current state for the given turn id."""
        return self._turn_index.get(turn_id)

    def get_active_turn(self, session_id: str) -> Optional[TurnState]:
        """Return the active turn for a session, if any."""
        return self._active_by_session.get(session_id)

    def request_cancel(self, *, session_id: Optional[str] = None, turn_id: Optional[str] = None) -> None:
        """Request cancellation of the active turn by session or explicit turn identifier."""
        state: Optional[TurnState] = None
        if turn_id:
            state = self._turn_index.get(turn_id)
        elif session_id:
            state = self._active_by_session.get(session_id)

        if state is None:
            logger.debug("Cancellation requested for unknown session/turn (%s, %s)", session_id, turn_id)
            return

        state.request_cancel()

    def check_cancelled(self, turn_id: str) -> bool:
        """Return True when the given turn has a pending cancellation request."""
        state = self._turn_index.get(turn_id)
        return bool(state and state.cancel_requested)

    def raise_if_cancelled(self, turn_id: str) -> None:
        """Raise asyncio.CancelledError if the turn has been marked for cancellation."""
        if self.check_cancelled(turn_id):
            logger.info("Turn %s cancellation acknowledged; raising CancelledError", turn_id)
            raise asyncio.CancelledError()

    async def fail_turn(self, turn_id: str, error: Exception) -> None:
        """Record a failure for the turn and release its slot."""
        await self.finish_turn(turn_id, status="failed", error=str(error))
