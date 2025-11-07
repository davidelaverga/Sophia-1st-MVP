"""Audio Queue Manager with Barge-In Support.

Manages audio segment playback queue with sub-200ms interruption capability.
Thread-safe for concurrent sessions.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable, Any
from threading import Lock

logger = logging.getLogger("sophia-backend")


class PlaybackState(Enum):
    """Audio playback states."""
    IDLE = "idle"
    PLAYING = "playing"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class AudioSegment:
    """Represents a single audio segment in the queue."""
    segment_id: str
    audio_data: bytes
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class QueueStats:
    """Statistics for audio queue monitoring."""
    session_id: str
    queue_length: int
    current_segment_id: Optional[str]
    state: PlaybackState
    segments_played: int
    segments_cancelled: int
    total_cancellations: int
    last_interruption_ms: Optional[float]


class AudioQueueManager:
    """Manages audio playback queue with barge-in support.

    Features:
    - Thread-safe queue operations for concurrent sessions
    - Sub-200ms interruption capability
    - No audio overlaps (sequential playback)
    - Session isolation
    - Graceful cleanup

    Usage:
        manager = AudioQueueManager()

        # Enqueue audio segment
        await manager.enqueue(session_id, audio_bytes, "audio/wav")

        # Start playback with callback
        async def send_audio(segment: AudioSegment):
            await websocket.send(segment.audio_data)

        await manager.start_playback(session_id, send_audio)

        # Interrupt on voice activity
        manager.cancel_current(session_id)
        manager.clear_queue(session_id)
    """

    def __init__(self, max_interruption_ms: float = 200.0):
        """Initialize audio queue manager.

        Args:
            max_interruption_ms: Maximum allowed interruption time in milliseconds
        """
        self._queues: Dict[str, deque] = {}
        self._states: Dict[str, PlaybackState] = {}
        self._current_segments: Dict[str, Optional[AudioSegment]] = {}
        self._playback_tasks: Dict[str, Optional[asyncio.Task]] = {}
        self._cancellation_events: Dict[str, asyncio.Event] = {}
        self._stats: Dict[str, Dict[str, int]] = {}

        self._lock = Lock()
        self._max_interruption_ms = max_interruption_ms

        logger.info(f"AudioQueueManager initialized (max_interruption={max_interruption_ms}ms)")

    def _init_session(self, session_id: str) -> None:
        """Initialize session-specific data structures."""
        with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = deque()
                self._states[session_id] = PlaybackState.IDLE
                self._current_segments[session_id] = None
                self._playback_tasks[session_id] = None
                self._cancellation_events[session_id] = asyncio.Event()
                self._stats[session_id] = {
                    "played": 0,
                    "cancelled": 0,
                    "total_cancellations": 0,
                    "last_interruption_ms": None,
                }
                logger.info(f"Session {session_id}: initialized")

    async def enqueue(
        self,
        session_id: str,
        audio_data: bytes,
        mime_type: str = "audio/wav",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Enqueue audio segment for playback.

        Args:
            session_id: Unique session identifier
            audio_data: Audio bytes to play
            mime_type: MIME type of audio data
            metadata: Optional metadata for the segment

        Returns:
            segment_id: Unique identifier for the enqueued segment
        """
        self._init_session(session_id)

        segment_id = f"{session_id}_{int(time.time() * 1000000)}"
        segment = AudioSegment(
            segment_id=segment_id,
            audio_data=audio_data,
            mime_type=mime_type,
            metadata=metadata or {},
        )

        with self._lock:
            self._queues[session_id].append(segment)
            queue_len = len(self._queues[session_id])

        logger.info(
            f"Session {session_id}: enqueued segment {segment_id} "
            f"({len(audio_data)} bytes, queue_len={queue_len})"
        )

        return segment_id

    async def start_playback(
        self,
        session_id: str,
        send_callback: Callable[[AudioSegment], Any],
    ) -> None:
        """Start asynchronous playback for session.

        Args:
            session_id: Session to start playback for
            send_callback: Async callback to send audio (receives AudioSegment)
        """
        self._init_session(session_id)

        # Cancel existing playback task if running
        if self._playback_tasks.get(session_id):
            logger.warning(f"Session {session_id}: stopping existing playback task")
            self._playback_tasks[session_id].cancel()
            try:
                await self._playback_tasks[session_id]
            except asyncio.CancelledError:
                pass

        # Start new playback task
        task = asyncio.create_task(self._playback_loop(session_id, send_callback))
        self._playback_tasks[session_id] = task

        logger.info(f"Session {session_id}: playback started")

    async def _playback_loop(
        self,
        session_id: str,
        send_callback: Callable[[AudioSegment], Any],
    ) -> None:
        """Internal playback loop - processes queue sequentially.

        Args:
            session_id: Session ID
            send_callback: Callback to send audio
        """
        try:
            while True:
                # Get next segment from queue
                segment = None
                with self._lock:
                    if self._queues[session_id]:
                        segment = self._queues[session_id].popleft()
                        self._states[session_id] = PlaybackState.PLAYING
                        self._current_segments[session_id] = segment
                    else:
                        self._states[session_id] = PlaybackState.IDLE
                        self._current_segments[session_id] = None

                if not segment:
                    # Queue empty - wait for new segments
                    await asyncio.sleep(0.1)
                    continue

                # Reset cancellation event
                self._cancellation_events[session_id].clear()

                # Play segment
                logger.info(
                    f"Session {session_id}: playing segment {segment.segment_id} "
                    f"({len(segment.audio_data)} bytes)"
                )

                playback_start = time.time()

                try:
                    # Send audio via callback
                    result = send_callback(segment)
                    if asyncio.iscoroutine(result):
                        await result

                    # Check for cancellation (barge-in)
                    if self._cancellation_events[session_id].is_set():
                        interruption_ms = (time.time() - playback_start) * 1000
                        logger.warning(
                            f"Session {session_id}: segment {segment.segment_id} "
                            f"interrupted after {interruption_ms:.1f}ms"
                        )

                        with self._lock:
                            self._stats[session_id]["cancelled"] += 1
                            self._stats[session_id]["last_interruption_ms"] = interruption_ms
                            self._states[session_id] = PlaybackState.CANCELLED

                        # Verify interruption time
                        if interruption_ms > self._max_interruption_ms:
                            logger.error(
                                f"Session {session_id}: interruption time {interruption_ms:.1f}ms "
                                f"exceeds limit {self._max_interruption_ms}ms"
                            )
                    else:
                        # Segment completed successfully
                        playback_duration = (time.time() - playback_start) * 1000
                        logger.info(
                            f"Session {session_id}: segment {segment.segment_id} "
                            f"completed in {playback_duration:.1f}ms"
                        )

                        with self._lock:
                            self._stats[session_id]["played"] += 1
                            self._states[session_id] = PlaybackState.COMPLETED

                except asyncio.CancelledError:
                    logger.info(f"Session {session_id}: playback task cancelled")
                    raise
                except Exception as e:
                    logger.error(
                        f"Session {session_id}: error playing segment {segment.segment_id}: {e}"
                    )

                finally:
                    with self._lock:
                        self._current_segments[session_id] = None

        except asyncio.CancelledError:
            logger.info(f"Session {session_id}: playback loop cancelled")
        except Exception as e:
            logger.error(f"Session {session_id}: playback loop error: {e}")

    def cancel_current(self, session_id: str) -> bool:
        """Cancel currently playing audio segment.

        Args:
            session_id: Session to cancel playback for

        Returns:
            True if segment was cancelled, False if nothing was playing
        """
        if session_id not in self._states:
            return False

        with self._lock:
            state = self._states.get(session_id, PlaybackState.IDLE)
            current = self._current_segments.get(session_id)
            if state == PlaybackState.PLAYING and current:
                self._cancellation_events[session_id].set()
                stats = self._stats.get(session_id)
                if stats is not None:
                    stats["total_cancellations"] += 1

                logger.info(
                    f"Session {session_id}: cancelled current segment {current.segment_id}"
                )
                return True

        return False

    def clear_queue(self, session_id: str) -> int:
        """Clear all pending segments from queue.

        Args:
            session_id: Session to clear queue for

        Returns:
            Number of segments cleared
        """
        if session_id not in self._queues:
            return 0

        with self._lock:
            count = len(self._queues[session_id])
            self._queues[session_id].clear()

        logger.info(f"Session {session_id}: cleared {count} segments from queue")
        return count

    def cancel_all(self, session_id: str) -> tuple[bool, int]:
        """Cancel current segment and clear entire queue.

        Args:
            session_id: Session to cancel all audio for

        Returns:
            Tuple of (current_cancelled, queue_cleared_count)
        """
        current_cancelled = self.cancel_current(session_id)
        queue_cleared = self.clear_queue(session_id)

        logger.info(
            f"Session {session_id}: cancelled all "
            f"(current={current_cancelled}, queued={queue_cleared})"
        )

        return current_cancelled, queue_cleared

    def get_stats(self, session_id: str) -> Optional[QueueStats]:
        """Get queue statistics for session.

        Args:
            session_id: Session to get stats for

        Returns:
            QueueStats object or None if session doesn't exist
        """
        if session_id not in self._states:
            return None

        with self._lock:
            stats = self._stats.get(session_id, {})
            queue_len = len(self._queues.get(session_id, []))
            current = self._current_segments.get(session_id)
            state = self._states.get(session_id, PlaybackState.IDLE)

        return QueueStats(
            session_id=session_id,
            queue_length=queue_len,
            current_segment_id=current.segment_id if current else None,
            state=state,
            segments_played=stats.get("played", 0),
            segments_cancelled=stats.get("cancelled", 0),
            total_cancellations=stats.get("total_cancellations", 0),
            last_interruption_ms=stats.get("last_interruption_ms"),
        )

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session resources.

        Args:
            session_id: Session to clean up
        """
        if session_id not in self._states:
            return

        # Cancel playback task
        task = self._playback_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Clear data structures
        with self._lock:
            self._queues.pop(session_id, None)
            self._states.pop(session_id, None)
            self._current_segments.pop(session_id, None)
            self._playback_tasks.pop(session_id, None)
            self._cancellation_events.pop(session_id, None)
            self._stats.pop(session_id, None)

        logger.info(f"Session {session_id}: cleaned up")

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs.

        Returns:
            List of session IDs with active queues
        """
        with self._lock:
            return list(self._states.keys())


# Global singleton instance
_audio_queue_manager: Optional[AudioQueueManager] = None


def get_audio_queue_manager() -> AudioQueueManager:
    """Get global AudioQueueManager instance.

    Returns:
        Singleton AudioQueueManager instance
    """
    global _audio_queue_manager
    if _audio_queue_manager is None:
        _audio_queue_manager = AudioQueueManager(max_interruption_ms=200.0)
    return _audio_queue_manager
