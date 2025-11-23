"""Performance monitoring utilities for load testing.

Provides real-time monitoring of system performance metrics during tests.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""

    timestamp: float
    active_sessions: int
    total_requests: int
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


@dataclass
class PerformanceMonitor:
    """Real-time performance monitoring during load tests."""

    sampling_interval_s: float = 1.0
    snapshots: List[PerformanceSnapshot] = field(default_factory=list)
    _is_running: bool = False
    _latencies: List[float] = field(default_factory=list)
    _request_count: int = 0
    _error_count: int = 0
    _active_sessions: int = 0
    _start_time: Optional[float] = None

    def start(self):
        """Start monitoring."""
        self._is_running = True
        self._start_time = time.time()
        logger.info("Performance monitoring started")

    def stop(self):
        """Stop monitoring."""
        self._is_running = False
        logger.info("Performance monitoring stopped")

    def record_request(self, latency_ms: float, success: bool = True):
        """Record a request with its latency."""
        self._latencies.append(latency_ms)
        self._request_count += 1
        if not success:
            self._error_count += 1

    def set_active_sessions(self, count: int):
        """Update active session count."""
        self._active_sessions = count

    async def capture_snapshot(self) -> PerformanceSnapshot:
        """Capture current performance metrics."""
        if not self._latencies:
            avg_latency = 0.0
            p50 = p95 = p99 = 0.0
        else:
            avg_latency = statistics.mean(self._latencies)
            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)
            p50 = sorted_latencies[int(n * 0.50)] if n > 0 else 0.0
            p95 = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
            p99 = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0

        elapsed_time = time.time() - (self._start_time or time.time())
        rps = self._request_count / elapsed_time if elapsed_time > 0 else 0.0
        error_rate = (
            self._error_count / self._request_count
            if self._request_count > 0
            else 0.0
        )

        # Try to get system metrics
        memory_mb = await self._get_memory_usage()
        cpu_percent = await self._get_cpu_usage()

        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            active_sessions=self._active_sessions,
            total_requests=self._request_count,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
        )

        self.snapshots.append(snapshot)
        return snapshot

    async def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return None

    async def _get_cpu_usage(self) -> Optional[float]:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return None

    async def run_monitoring_loop(self):
        """Run continuous monitoring loop."""
        while self._is_running:
            await self.capture_snapshot()
            await asyncio.sleep(self.sampling_interval_s)

    def print_summary(self):
        """Print performance summary."""
        if not self.snapshots:
            logger.warning("No snapshots captured")
            return

        logger.info("\n" + "=" * 60)
        logger.info("PERFORMANCE MONITORING SUMMARY")
        logger.info("=" * 60)

        # Overall stats
        total_duration = (
            self.snapshots[-1].timestamp - self.snapshots[0].timestamp
        )
        avg_rps = statistics.mean([s.requests_per_second for s in self.snapshots])
        avg_latency = statistics.mean([s.avg_latency_ms for s in self.snapshots])
        max_p95 = max([s.p95_latency_ms for s in self.snapshots])
        max_p99 = max([s.p99_latency_ms for s in self.snapshots])
        avg_error_rate = statistics.mean([s.error_rate for s in self.snapshots])

        logger.info(f"Duration: {total_duration:.2f}s")
        logger.info(f"Average RPS: {avg_rps:.1f}")
        logger.info(f"Average latency: {avg_latency:.1f}ms")
        logger.info(f"Max P95 latency: {max_p95:.1f}ms")
        logger.info(f"Max P99 latency: {max_p99:.1f}ms")
        logger.info(f"Average error rate: {avg_error_rate * 100:.2f}%")

        # System resource usage (if available)
        memory_samples = [s.memory_usage_mb for s in self.snapshots if s.memory_usage_mb]
        cpu_samples = [s.cpu_usage_percent for s in self.snapshots if s.cpu_usage_percent]

        if memory_samples:
            avg_memory = statistics.mean(memory_samples)
            max_memory = max(memory_samples)
            logger.info(f"Memory: avg={avg_memory:.1f}MB, max={max_memory:.1f}MB")

        if cpu_samples:
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)
            logger.info(f"CPU: avg={avg_cpu:.1f}%, max={max_cpu:.1f}%")

        logger.info("=" * 60)

    def export_to_csv(self, filename: str):
        """Export snapshots to CSV file."""
        import csv

        with open(filename, 'w', newline='') as f:
            if not self.snapshots:
                return

            fieldnames = [
                'timestamp',
                'active_sessions',
                'total_requests',
                'requests_per_second',
                'avg_latency_ms',
                'p50_latency_ms',
                'p95_latency_ms',
                'p99_latency_ms',
                'error_rate',
                'memory_usage_mb',
                'cpu_usage_percent',
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for snapshot in self.snapshots:
                writer.writerow({
                    'timestamp': snapshot.timestamp,
                    'active_sessions': snapshot.active_sessions,
                    'total_requests': snapshot.total_requests,
                    'requests_per_second': snapshot.requests_per_second,
                    'avg_latency_ms': snapshot.avg_latency_ms,
                    'p50_latency_ms': snapshot.p50_latency_ms,
                    'p95_latency_ms': snapshot.p95_latency_ms,
                    'p99_latency_ms': snapshot.p99_latency_ms,
                    'error_rate': snapshot.error_rate,
                    'memory_usage_mb': snapshot.memory_usage_mb or '',
                    'cpu_usage_percent': snapshot.cpu_usage_percent or '',
                })

        logger.info(f"Performance data exported to {filename}")


@dataclass
class MetricsCollector:
    """Collect and aggregate metrics from multiple sources."""

    session_metrics: Dict[str, List[float]] = field(default_factory=dict)

    def record(self, session_id: str, metric_name: str, value: float):
        """Record a metric value."""
        key = f"{session_id}:{metric_name}"
        if key not in self.session_metrics:
            self.session_metrics[key] = []
        self.session_metrics[key].append(value)

    def get_percentile(
        self,
        session_id: str,
        metric_name: str,
        percentile: float
    ) -> Optional[float]:
        """Get percentile value for a metric."""
        key = f"{session_id}:{metric_name}"
        values = self.session_metrics.get(key, [])
        if not values:
            return None

        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def get_aggregate_percentile(
        self,
        metric_name: str,
        percentile: float
    ) -> Optional[float]:
        """Get aggregate percentile across all sessions."""
        all_values = []
        for key, values in self.session_metrics.items():
            if metric_name in key:
                all_values.extend(values)

        if not all_values:
            return None

        sorted_values = sorted(all_values)
        idx = int(len(sorted_values) * percentile)
        return sorted_values[min(idx, len(sorted_values) - 1)]
