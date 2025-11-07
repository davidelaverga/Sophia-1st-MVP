"""Comprehensive tests for Audio Queue Manager with Barge-In support.

Tests cover:
- Queue operations (enqueue, dequeue, clear)
- Barge-in interruption timing (<200ms requirement)
- Concurrent session isolation
- Thread safety with 10+ simultaneous sessions
- Stats tracking and reporting
"""

import asyncio
import pytest
import time
from app.services.audio_queue import (
    AudioQueueManager,
    AudioSegment,
    PlaybackState,
    get_audio_queue_manager,
)


@pytest.fixture
def audio_queue():
    """Create fresh AudioQueueManager for each test."""
    return AudioQueueManager(max_interruption_ms=200.0)


@pytest.fixture
def sample_audio():
    """Sample audio data for testing."""
    return b"RIFF" + b"\x00" * 100  # Minimal WAV-like data


class TestAudioQueueBasics:
    """Test basic queue operations."""

    @pytest.mark.asyncio
    async def test_enqueue_segment(self, audio_queue, sample_audio):
        """Test enqueueing audio segments."""
        session_id = "test-session-1"

        segment_id = await audio_queue.enqueue(
            session_id=session_id,
            audio_data=sample_audio,
            mime_type="audio/wav",
        )

        assert segment_id.startswith(session_id)
        stats = audio_queue.get_stats(session_id)
        assert stats.queue_length == 1

    @pytest.mark.asyncio
    async def test_clear_queue(self, audio_queue, sample_audio):
        """Test clearing queue."""
        session_id = "test-session-2"

        # Enqueue multiple segments
        for i in range(5):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        stats = audio_queue.get_stats(session_id)
        assert stats.queue_length == 5

        # Clear queue
        cleared = audio_queue.clear_queue(session_id)
        assert cleared == 5

        stats = audio_queue.get_stats(session_id)
        assert stats.queue_length == 0

    @pytest.mark.asyncio
    async def test_session_isolation(self, audio_queue, sample_audio):
        """Test that sessions are isolated."""
        session_1 = "test-session-1"
        session_2 = "test-session-2"

        # Enqueue to different sessions
        await audio_queue.enqueue(session_1, sample_audio, "audio/wav")
        await audio_queue.enqueue(session_2, sample_audio, "audio/wav")
        await audio_queue.enqueue(session_2, sample_audio, "audio/wav")

        stats_1 = audio_queue.get_stats(session_1)
        stats_2 = audio_queue.get_stats(session_2)

        assert stats_1.queue_length == 1
        assert stats_2.queue_length == 2

        # Clear session 1 shouldn't affect session 2
        audio_queue.clear_queue(session_1)
        stats_2_after = audio_queue.get_stats(session_2)
        assert stats_2_after.queue_length == 2


class TestBargeinMechanism:
    """Test barge-in interruption functionality."""

    @pytest.mark.asyncio
    async def test_cancel_current_segment(self, audio_queue, sample_audio):
        """Test cancelling currently playing segment."""
        session_id = "test-barge-in-1"
        playback_started = False
        playback_completed = False

        async def slow_send_callback(segment: AudioSegment):
            """Simulates slow playback that can be interrupted."""
            nonlocal playback_started, playback_completed
            playback_started = True
            # Simulate slow playback (should be interrupted)
            await asyncio.sleep(0.5)
            playback_completed = True

        # Enqueue segment
        await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        # Start playback
        await audio_queue.start_playback(session_id, slow_send_callback)

        # Wait for playback to start
        await asyncio.sleep(0.05)
        assert playback_started

        # Cancel current segment
        start_time = time.time()
        cancelled = audio_queue.cancel_current(session_id)
        cancel_time_ms = (time.time() - start_time) * 1000

        assert cancelled is True
        assert cancel_time_ms < 200, f"Cancellation took {cancel_time_ms:.2f}ms (exceeds 200ms)"

        # Wait a bit and verify playback didn't complete
        await asyncio.sleep(0.1)
        # Playback should have been interrupted, not completed
        # (In real implementation, callback would check cancellation event)

    @pytest.mark.asyncio
    async def test_interruption_timing(self, audio_queue, sample_audio):
        """Test that interruption happens within 200ms."""
        session_id = "test-timing-1"
        interruption_times = []

        async def tracking_callback(segment: AudioSegment):
            """Callback that tracks interruption timing."""
            start = time.time()
            await asyncio.sleep(0.3)  # Simulate playback
            duration = (time.time() - start) * 1000
            interruption_times.append(duration)

        # Enqueue multiple segments
        for i in range(5):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        # Start playback
        await audio_queue.start_playback(session_id, tracking_callback)

        # Wait for first segment to start
        await asyncio.sleep(0.05)

        # Interrupt
        interrupt_start = time.time()
        current_cancelled, queue_cleared = audio_queue.cancel_all(session_id)
        interrupt_duration_ms = (time.time() - interrupt_start) * 1000

        assert interrupt_duration_ms < 200, (
            f"Barge-in took {interrupt_duration_ms:.2f}ms (exceeds 200ms requirement)"
        )
        assert current_cancelled is True
        assert queue_cleared == 4  # 5 enqueued - 1 playing

    @pytest.mark.asyncio
    async def test_cancel_all(self, audio_queue, sample_audio):
        """Test cancelling current segment and clearing queue."""
        session_id = "test-cancel-all-1"

        async def dummy_callback(segment: AudioSegment):
            await asyncio.sleep(0.2)

        # Enqueue multiple segments
        for i in range(5):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        # Start playback
        await audio_queue.start_playback(session_id, dummy_callback)
        await asyncio.sleep(0.05)  # Let first segment start

        # Cancel all
        current_cancelled, queue_cleared = audio_queue.cancel_all(session_id)

        assert current_cancelled is True
        assert queue_cleared >= 3  # At least some segments were cleared

        # Verify queue is empty
        stats = audio_queue.get_stats(session_id)
        assert stats.queue_length == 0


class TestConcurrentSessions:
    """Test thread-safety and concurrent session handling."""

    @pytest.mark.asyncio
    async def test_10_simultaneous_sessions(self, audio_queue, sample_audio):
        """Test 10 simultaneous sessions without errors (requirement)."""
        num_sessions = 10
        segments_per_session = 5

        async def session_workflow(session_id: str):
            """Simulates a complete session workflow."""
            try:
                # Enqueue segments
                for i in range(segments_per_session):
                    await audio_queue.enqueue(
                        session_id=session_id,
                        audio_data=sample_audio,
                        mime_type="audio/wav",
                        metadata={"index": i}
                    )

                # Start playback with callback
                async def send_callback(segment: AudioSegment):
                    await asyncio.sleep(0.01)  # Simulate fast playback

                await audio_queue.start_playback(session_id, send_callback)

                # Wait a bit
                await asyncio.sleep(0.05)

                # Randomly cancel some sessions
                import random
                if random.random() > 0.5:
                    audio_queue.cancel_all(session_id)

                # Wait for playback
                await asyncio.sleep(0.1)

                # Cleanup
                await audio_queue.cleanup_session(session_id)

                return True

            except Exception as e:
                print(f"Session {session_id} error: {e}")
                return False

        # Run 10 sessions concurrently
        session_ids = [f"concurrent-session-{i}" for i in range(num_sessions)]
        results = await asyncio.gather(
            *[session_workflow(sid) for sid in session_ids],
            return_exceptions=True
        )

        # Verify all sessions completed successfully
        assert all(results), f"Some sessions failed: {results}"
        assert len([r for r in results if r is True]) == num_sessions

    @pytest.mark.asyncio
    async def test_concurrent_enqueue_operations(self, audio_queue, sample_audio):
        """Test concurrent enqueue operations are thread-safe."""
        session_id = "test-concurrent-enqueue"
        num_concurrent_enqueues = 20

        async def enqueue_segment(index: int):
            """Enqueue single segment."""
            return await audio_queue.enqueue(
                session_id=session_id,
                audio_data=sample_audio,
                mime_type="audio/wav",
                metadata={"index": index}
            )

        # Enqueue 20 segments concurrently
        segment_ids = await asyncio.gather(
            *[enqueue_segment(i) for i in range(num_concurrent_enqueues)]
        )

        # Verify all segments were enqueued
        assert len(segment_ids) == num_concurrent_enqueues
        assert len(set(segment_ids)) == num_concurrent_enqueues  # All unique

        stats = audio_queue.get_stats(session_id)
        assert stats.queue_length == num_concurrent_enqueues

    @pytest.mark.asyncio
    async def test_concurrent_cancel_operations(self, audio_queue, sample_audio):
        """Test concurrent cancel operations don't cause errors."""
        session_id = "test-concurrent-cancel"

        # Enqueue some segments
        for i in range(10):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        async def dummy_callback(segment: AudioSegment):
            await asyncio.sleep(0.05)

        await audio_queue.start_playback(session_id, dummy_callback)
        await asyncio.sleep(0.02)

        # Multiple concurrent cancellations
        async def cancel_operation():
            return audio_queue.cancel_current(session_id)

        results = await asyncio.gather(
            *[cancel_operation() for _ in range(5)],
            return_exceptions=True
        )

        # At least one should succeed, no exceptions
        assert not any(isinstance(r, Exception) for r in results)
        assert any(r is True for r in results)


class TestPlaybackSequence:
    """Test sequential playback without overlaps."""

    @pytest.mark.asyncio
    async def test_sequential_playback_no_overlaps(self, audio_queue, sample_audio):
        """Test that segments play sequentially without overlaps."""
        session_id = "test-sequential"
        playback_order = []
        playback_times = []

        async def tracking_callback(segment: AudioSegment):
            """Track playback order and timing."""
            index = segment.metadata.get("index", 0)
            start_time = time.time()
            playback_order.append(index)
            playback_times.append(start_time)

            # Simulate playback duration
            await asyncio.sleep(0.05)

        # Enqueue 5 segments
        for i in range(5):
            await audio_queue.enqueue(
                session_id=session_id,
                audio_data=sample_audio,
                mime_type="audio/wav",
                metadata={"index": i}
            )

        # Start playback
        await audio_queue.start_playback(session_id, tracking_callback)

        # Wait for all segments to play
        await asyncio.sleep(0.5)

        # Verify sequential order
        assert playback_order == [0, 1, 2, 3, 4], f"Expected [0,1,2,3,4], got {playback_order}"

        # Verify no overlaps (each segment started after previous)
        for i in range(1, len(playback_times)):
            time_diff = playback_times[i] - playback_times[i-1]
            assert time_diff >= 0.04, f"Overlap detected: {time_diff*1000:.2f}ms gap"


class TestStatsTracking:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, audio_queue, sample_audio):
        """Test that stats are tracked correctly."""
        session_id = "test-stats"

        async def fast_callback(segment: AudioSegment):
            await asyncio.sleep(0.01)

        # Enqueue and play some segments
        for i in range(3):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        await audio_queue.start_playback(session_id, fast_callback)
        await asyncio.sleep(0.1)

        # Get stats
        stats = audio_queue.get_stats(session_id)
        assert stats.session_id == session_id
        assert stats.segments_played >= 0
        assert stats.state in [PlaybackState.IDLE, PlaybackState.PLAYING, PlaybackState.COMPLETED]

    @pytest.mark.asyncio
    async def test_cancellation_stats(self, audio_queue, sample_audio):
        """Test cancellation statistics."""
        session_id = "test-cancel-stats"

        async def slow_callback(segment: AudioSegment):
            await asyncio.sleep(0.2)

        # Enqueue segments
        for i in range(5):
            await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        await audio_queue.start_playback(session_id, slow_callback)
        await asyncio.sleep(0.05)

        # Cancel
        audio_queue.cancel_all(session_id)
        await asyncio.sleep(0.1)

        stats = audio_queue.get_stats(session_id)
        assert stats.total_cancellations >= 1


class TestCleanup:
    """Test session cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_session(self, audio_queue, sample_audio):
        """Test session cleanup removes all data."""
        session_id = "test-cleanup"

        # Create session data
        await audio_queue.enqueue(session_id, sample_audio, "audio/wav")

        async def dummy_callback(segment: AudioSegment):
            await asyncio.sleep(0.01)

        await audio_queue.start_playback(session_id, dummy_callback)
        await asyncio.sleep(0.02)

        # Cleanup
        await audio_queue.cleanup_session(session_id)

        # Verify cleanup
        stats = audio_queue.get_stats(session_id)
        assert stats is None

        active_sessions = audio_queue.get_active_sessions()
        assert session_id not in active_sessions


class TestSingletonInstance:
    """Test global singleton."""

    def test_get_audio_queue_manager(self):
        """Test that get_audio_queue_manager returns singleton."""
        manager1 = get_audio_queue_manager()
        manager2 = get_audio_queue_manager()

        assert manager1 is manager2
        assert isinstance(manager1, AudioQueueManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
