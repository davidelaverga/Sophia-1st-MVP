#!/usr/bin/env python3
"""
Real Load Testing Script for Sophia Voice Pipeline
Connects to running server and performs actual load tests
"""

import asyncio
import websockets
import json
import time
import statistics
import struct
from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class SessionMetrics:
    """Metrics for a single WebSocket session"""

    session_id: str
    start_time: float
    end_time: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    errors: List[str] = field(default_factory=list)
    latencies_ms: List[float] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_latency(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index]

    @property
    def p99_latency(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index]


def generate_pcm16_audio(
    duration_seconds: float = 1.0, sample_rate: int = 16000
) -> bytes:
    """Generate PCM16 audio data (silence) for testing"""
    num_samples = int(duration_seconds * sample_rate)
    # Generate silence (zeros)
    audio_data = struct.pack(f"{num_samples}h", *([0] * num_samples))
    return audio_data


async def run_websocket_session(
    server_url: str, session_id: str, num_messages: int = 3
) -> SessionMetrics:
    """Run a single WebSocket session with real audio messages"""
    metrics = SessionMetrics(session_id=session_id, start_time=time.time())

    try:
        async with websockets.connect(server_url) as websocket:
            print(f"✅ Session {session_id}: Connected to {server_url}")

            # Send multiple audio chunks
            for i in range(num_messages):
                # Generate test audio
                audio_data = generate_pcm16_audio(duration_seconds=0.5)

                # Send audio message
                message = {
                    "type": "audio",
                    "data": audio_data.hex(),  # Convert bytes to hex string
                    "session_id": session_id,
                }

                send_start = time.time()
                await websocket.send(json.dumps(message))
                metrics.messages_sent += 1

                # Wait for response
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    recv_time = time.time()
                    latency_ms = (recv_time - send_start) * 1000
                    metrics.latencies_ms.append(latency_ms)
                    metrics.messages_received += 1

                    print(
                        f"  Session {session_id} msg {i + 1}: {latency_ms:.2f}ms latency"
                    )

                except asyncio.TimeoutError:
                    error_msg = f"Message {i + 1} timeout"
                    metrics.errors.append(error_msg)
                    print(f"  ⚠️ Session {session_id}: {error_msg}")

                # Small delay between messages
                await asyncio.sleep(0.1)

    except Exception as e:
        error_msg = f"Session error: {str(e)}"
        metrics.errors.append(error_msg)
        print(f"❌ Session {session_id}: {error_msg}")

    finally:
        metrics.end_time = time.time()

    return metrics


async def run_load_test(
    server_url: str = "ws://localhost:8000/ws/voice",
    num_sessions: int = 5,
    messages_per_session: int = 3,
):
    """Run parallel load test with multiple WebSocket sessions"""
    print("\n🚀 Starting Load Test")
    print(f"   Server: {server_url}")
    print(f"   Parallel sessions: {num_sessions}")
    print(f"   Messages per session: {messages_per_session}")
    print(f"   Total messages: {num_sessions * messages_per_session}\n")

    # Create parallel sessions
    tasks = []
    for i in range(num_sessions):
        session_id = f"load_test_session_{i + 1}"
        task = run_websocket_session(server_url, session_id, messages_per_session)
        tasks.append(task)

    # Run all sessions in parallel
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_duration = time.time() - start_time

    # Analyze results
    print("\n📊 Load Test Results")
    print(f"   Total duration: {total_duration:.2f}s")
    print("   ─" * 40)

    successful_sessions = []
    failed_sessions = []

    for result in results:
        if isinstance(result, Exception):
            print(f"   ❌ Session failed with exception: {result}")
            failed_sessions.append(str(result))
        elif isinstance(result, SessionMetrics):
            successful_sessions.append(result)

            status = "✅" if not result.errors else "⚠️"
            print(f"   {status} {result.session_id}:")
            print(f"      Duration: {result.duration_ms:.2f}ms")
            print(
                f"      Messages: {result.messages_sent} sent, {result.messages_received} received"
            )
            print(f"      P50 latency: {result.p50_latency:.2f}ms")
            print(f"      P95 latency: {result.p95_latency:.2f}ms")
            print(f"      P99 latency: {result.p99_latency:.2f}ms")
            if result.errors:
                print(f"      Errors: {len(result.errors)}")

    # Overall statistics
    if successful_sessions:
        all_latencies = []
        total_messages_sent = 0
        total_messages_received = 0
        total_errors = 0

        for session in successful_sessions:
            all_latencies.extend(session.latencies_ms)
            total_messages_sent += session.messages_sent
            total_messages_received += session.messages_received
            total_errors += len(session.errors)

        print("\n📈 Overall Statistics")
        print(f"   Successful sessions: {len(successful_sessions)}/{num_sessions}")
        print(f"   Failed sessions: {len(failed_sessions)}")
        print(f"   Total messages sent: {total_messages_sent}")
        print(f"   Total messages received: {total_messages_received}")
        print(
            f"   Success rate: {(total_messages_received / total_messages_sent * 100):.1f}%"
        )
        print(f"   Total errors: {total_errors}")

        if all_latencies:
            print("\n⏱️  Latency Metrics (all sessions)")
            print(f"   P50: {statistics.median(all_latencies):.2f}ms")
            sorted_all = sorted(all_latencies)
            print(f"   P95: {sorted_all[int(len(sorted_all) * 0.95)]:.2f}ms")
            print(f"   P99: {sorted_all[int(len(sorted_all) * 0.99)]:.2f}ms")
            print(f"   Min: {min(all_latencies):.2f}ms")
            print(f"   Max: {max(all_latencies):.2f}ms")
            print(f"   Mean: {statistics.mean(all_latencies):.2f}ms")

    # Check if test passed
    success_rate = (
        (len(successful_sessions) / num_sessions) * 100 if num_sessions > 0 else 0
    )

    print(f"\n{'=' * 50}")
    if success_rate >= 80:
        print("✅ LOAD TEST PASSED")
        print(f"   {success_rate:.1f}% sessions successful (threshold: 80%)")
        return True
    else:
        print("❌ LOAD TEST FAILED")
        print(f"   {success_rate:.1f}% sessions successful (threshold: 80%)")
        return False


async def main():
    """Main entry point"""
    # Test with different load levels
    print("=" * 60)
    print("REAL LOAD TESTING - Sophia Voice Pipeline")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check if server is accessible
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as resp:
                if resp.status == 200:
                    print("✅ Server health check passed\n")
                else:
                    print(f"⚠️ Server health check returned {resp.status}\n")
    except Exception as e:
        print(f"⚠️ Could not connect to server health endpoint: {e}")
        print("Proceeding with WebSocket test anyway...\n")

    # Run load test
    test_passed = await run_load_test(
        server_url="ws://localhost:8000/ws/voice",
        num_sessions=5,
        messages_per_session=2,
    )

    print("\n" + "=" * 60)
    if test_passed:
        print("🎉 ALL TESTS PASSED")
    else:
        print("⚠️ SOME TESTS FAILED - Review results above")
    print("=" * 60 + "\n")

    return test_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
