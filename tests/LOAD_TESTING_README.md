# Integration Load Testing (Task #42713)

Comprehensive load testing suite for Sophia's voice-text pipeline.

## Overview

Tests system stability and performance under concurrent load with 5-10 parallel WebSocket sessions. Validates graceful fallback when services fail (DB, LLM, TTS).

## Test Components

### 1. Parallel Session Testing (`test_integration_load.py`)

Tests multiple concurrent WebSocket sessions:
- **5 parallel sessions**: Baseline load test
- **10 parallel sessions**: High load test
- Captures latency metrics (P50/P95/P99)
- Tracks error rates and throughput

**Run:**
```bash
uv run python -m pytest tests/test_integration_load.py -v
```

**Expected Results:**
- Success rate ≥ 80% for 5 sessions
- Success rate ≥ 70% for 10 sessions
- P95 latency < 5000ms for 5 sessions
- P95 latency < 7000ms for 10 sessions

### 2. Service Failure Testing (`test_service_fallbacks.py`)

Tests graceful fallback mechanisms:
- **Database failures**: Redis → Supabase → In-memory
- **LLM failures**: Mistral → Claude → Error message
- **TTS failures**: Inworld → OpenAI → Silent audio

**Run:**
```bash
uv run python -m pytest tests/test_service_fallbacks.py -v
```

**Expected Results:**
- All fallback chains execute correctly
- No crashes or unhandled exceptions
- Graceful degradation with user-friendly messages

### 3. Performance Monitoring (`tests/utils/performance_monitor.py`)

Real-time performance tracking:
- Requests per second (RPS)
- Latency percentiles (P50/P95/P99)
- Error rates
- Memory and CPU usage

**Usage:**
```python
from tests.utils import PerformanceMonitor

monitor = PerformanceMonitor(sampling_interval_s=1.0)
monitor.start()

# Run your tests...

monitor.stop()
monitor.print_summary()
monitor.export_to_csv("results.csv")
```

## Running All Tests

Run complete load testing suite:

```bash
# Run all load tests
uv run python -m pytest tests/test_integration_load.py tests/test_service_fallbacks.py -v

# Run with detailed output
uv run python -m pytest tests/test_integration_load.py tests/test_service_fallbacks.py -v -s

# Run specific test class
uv run python -m pytest tests/test_integration_load.py::TestParallelSessions -v
```

## Interpreting Results

### Success Metrics

✅ **PASSING CRITERIA:**
- Overall success rate ≥ 70%
- P95 latency < 7000ms
- Error rate < 20%
- All fallback mechanisms work
- No unhandled exceptions

❌ **FAILING CRITERIA:**
- Success rate < 70%
- P95 latency > 10000ms
- Crashes or unhandled exceptions
- Fallback chains don't execute

### Example Output

```
LOAD TEST RESULTS
============================================================
Total sessions: 10
Successful: 9
Failed: 1
Success rate: 90.0%
Total duration: 45.23s
Aggregate P50 latency: 234.5ms
Aggregate P95 latency: 1856.2ms
============================================================

Session a3f2b1c8:
  Duration: 42.15s
  Messages sent: 80
  Messages received: 78
  Success rate: 97.5%
  P50 latency: 198.3ms
  P95 latency: 1245.7ms
```

## Performance Benchmarks

### Target Metrics (Task #42713)

| Metric | Target | Acceptable |
|--------|--------|------------|
| P50 Latency | < 500ms | < 1000ms |
| P95 Latency | < 2000ms | < 5000ms |
| Success Rate | ≥ 90% | ≥ 70% |
| Error Rate | < 5% | < 20% |
| Throughput | ≥ 10 msg/s | ≥ 5 msg/s |

### Service-Specific Targets

**Database:**
- P95 query time: < 100ms
- Connection pool: Handle 10+ concurrent sessions
- Fallback time: < 200ms

**LLM:**
- P95 response time: < 3000ms
- Timeout threshold: 10s
- Fallback to Claude: < 500ms overhead

**TTS:**
- P95 generation time: < 2000ms
- Fallback to OpenAI: < 300ms overhead
- Silent audio fallback: < 50ms

## Troubleshooting

### Common Issues

**1. Tests timeout:**
```bash
# Increase pytest timeout
uv run python -m pytest tests/test_integration_load.py --timeout=300
```

**2. High latency:**
- Check network connectivity
- Verify service API keys are valid
- Check for rate limiting

**3. Service fallbacks not triggered:**
- Ensure mock patches are applied correctly
- Check failure rate settings
- Verify fallback logic is enabled

### Debug Mode

Run with debug logging:
```bash
uv run python -m pytest tests/test_integration_load.py -v -s --log-cli-level=DEBUG
```

## Continuous Integration

Add to CI pipeline:

```yaml
# .github/workflows/load-tests.yml
name: Load Tests
on: [push, pull_request]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run load tests
        run: |
          uv sync
          uv run python -m pytest tests/test_integration_load.py -v
          uv run python -m pytest tests/test_service_fallbacks.py -v
```

## Checklist Verification

Task #42713 Checklist:

- [x] 1. **Автоматический тест-харнес для 5-10 параллельных потоков**
  - `test_integration_load.py::test_5_parallel_sessions`
  - `test_integration_load.py::test_10_parallel_sessions`

- [x] 2. **Имитация краха сервисов с graceful fallback**
  - `test_service_fallbacks.py::TestDatabaseFallback`
  - `test_service_fallbacks.py::TestLLMFallback`
  - `test_service_fallbacks.py::TestTTSFallback`

- [x] 3. **Захват и проверка латентностей на P50/P95**
  - `test_integration_load.py::TestLatencyMetrics`
  - `performance_monitor.py::PerformanceMonitor`

- [x] 4. **Мониторинг метрик производительности**
  - `performance_monitor.py::PerformanceMonitor`
  - Real-time RPS, latency, error rate tracking
  - CSV export for analysis

## Future Enhancements

- [ ] Add WebSocket integration tests with real server
- [ ] Implement stress testing (50+ sessions)
- [ ] Add chaos engineering (random service kills)
- [ ] Performance regression tracking
- [ ] Grafana dashboard integration
- [ ] Distributed load testing support

## References

- Task: #42713 - Integration Load Testing
- Related: #42333 - Audio Queue Barge-In
- Docs: `docs/QUICKSTART_AUDIO_QUEUE.md`
