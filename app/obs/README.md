# Observability Module

Prometheus metrics for monitoring Sophia voice backend routing system (M3 milestone).

## Metrics

### `intent_total`
Counter tracking intent classifications.

**Labels:**
- `intent`: `emotional_support` or `utility`

**Example:**
```python
from app.obs.metrics import track_intent
track_intent("emotional_support")
```

### `mode_total`
Counter tracking mode routings.

**Labels:**
- `mode`: `emotional_support`, `utility_direct`, `utility_light`, or `utility_agentic`

**Example:**
```python
from app.obs.metrics import track_mode
track_mode("utility_light")
```

### `utility_path_total`
Counter tracking utility path selections (only for utility intents).

**Labels:**
- `path`: `direct`, `light`, or `agentic`

**Example:**
```python
from app.obs.metrics import track_utility_path
track_utility_path("agentic")
```

## Deprecated DeFi Metrics

The following metrics are **DEPRECATED** and should **NOT** be used in M3:

- `defi_intent_counter` - DeFi intent classifications (REMOVED)
- `defi_rag_latency` - DeFi RAG query latency (REMOVED)
- `defi_faq_category_requests` - DeFi FAQ categories (REMOVED)

Customer requirement: Stop tracking DeFi-specific metrics. Code remains commented for reference only.

## Integration

Metrics are automatically tracked in `app/routing/intent_router.py` when classification occurs:

```python
from app.obs.metrics import track_intent, track_mode, track_utility_path

# Emotional support flow
track_intent(Intent.EMOTIONAL_SUPPORT.value)
track_mode(CurrentMode.EMOTIONAL_SUPPORT.value)

# Utility flow
track_intent(Intent.UTILITY.value)
track_mode(current_mode.value)
track_utility_path(utility_path.value)
```

## Testing

### Local (if dependencies installed):
```bash
pytest tests/test_intent_and_metrics.py -v
```

### Docker (recommended):
```bash
docker exec sophia-backend python3 -m pytest /app/tests/test_intent_and_metrics.py -v
```

### Expected Results:
```
16 passed in ~18s

✅ 3 tests: Emotional vs Utility classification
✅ 4 tests: Utility path routing (DIRECT/LIGHT/AGENTIC)
✅ 2 tests: Reflection keywords → AGENTIC
✅ 2 tests: LangGraph state population
✅ 5 tests: Prometheus metrics incrementation
```

### Test Coverage:
- Intent classification (emotional vs utility)
- Utility path routing (direct vs light vs agentic)
- LangGraph node integration
- Metrics increment verification

### Troubleshooting:
If you get `ModuleNotFoundError: No module named 'prometheus_client'`:
```bash
pip install prometheus-client
# Or in Docker:
docker exec sophia-backend pip install prometheus-client
```
