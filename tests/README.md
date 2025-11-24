# Sophia Testing Suite

Комплексная система тестирования для Sophia backend.

## Структура тестов

```
tests/
├── README.md                          # Этот файл
├── LOAD_TESTING_README.md             # Документация load testing
├── REAL_INTEGRATION_TESTING.md        # Real integration тесты
│
├── Unit Tests (pytest):
│   ├── test_intent_and_metrics.py     # Task #42731: Intent routing + Prometheus metrics
│   ├── test_intent_router.py          # Intent classification тесты
│   ├── test_utility_router.py         # Utility path routing
│   ├── test_tier0_classifier.py       # Tier-0 классификатор
│   ├── test_routing_skills.py         # Skill routing
│   ├── test_emotion_*.py              # Emotion detection тесты
│   ├── test_memory_manager.py         # Memory system
│   └── test_*.py                      # Другие unit тесты
│
├── Integration Tests (pytest):
│   ├── test_integration_load.py       # Mock-based integration тесты
│   ├── test_service_fallbacks.py      # Service fallback тесты
│   └── test_main.py                   # API endpoint тесты
│
├── Load Test Scripts (run directly):
│   ├── load_test_final.py             # Простой production load test
│   ├── comprehensive_load_test.py     # Полный load test (4 checklist)
│   ├── run_load_test.py               # Deprecated
│   └── run_real_load_test.py          # Deprecated
│
├── E2E Tests (run directly):
│   ├── test_sophia_langgraph.py       # Полный LangGraph pipeline тест
│   ├── test_sophia_api.py             # API endpoint тесты
│   └── test_real_websocket_integration.py  # Real WebSocket тесты
│
└── Utils:
    └── utils/
        └── performance_monitor.py     # Performance monitoring utilities
```

---

## Быстрый старт

### 1. Unit тесты (pytest)

Запуск ВСЕХ unit тестов:

```bash
# Локально (если есть зависимости)
pytest tests/ --ignore=tests/comprehensive_load_test.py --ignore=tests/load_test_final.py -v

# В Docker контейнере (рекомендуется)
docker exec sophia-backend python3 -m pytest /app/tests/ \
  --ignore=/app/tests/comprehensive_load_test.py \
  --ignore=/app/tests/load_test_final.py \
  --ignore=/app/tests/run_load_test.py \
  --ignore=/app/tests/run_real_load_test.py \
  -v
```

Запуск конкретного теста:

```bash
# Task #42731: Intent routing + metrics
pytest tests/test_intent_and_metrics.py -v

# Tier-0 classifier
pytest tests/test_tier0_classifier.py -v

# Emotion detection
pytest tests/test_emotion_guided_prompt.py -v
```

### 2. Load тесты (запускать напрямую)

⚠️ **ВАЖНО**: Load test скрипты НЕ запускаются через pytest!

```bash
# Простой load test (рекомендуется для CI/CD)
docker exec sophia-backend python3 /app/tests/load_test_final.py

# Полный comprehensive load test (все 4 checklist пункта)
docker exec sophia-backend python3 /app/tests/comprehensive_load_test.py
```

**Требования:**
- Docker контейнер должен быть запущен: `docker-compose up -d`
- Redis должен быть доступен
- Все сервисы (Mistral, Inworld) должны быть настроены

### 3. E2E тесты (запускать напрямую)

```bash
# Полный LangGraph pipeline тест
python tests/test_sophia_langgraph.py

# API endpoint тесты
python tests/test_sophia_api.py

# Real WebSocket integration
python tests/test_real_websocket_integration.py
```

---

## Тесты по задачам

### Task #42731: Intent Routing + Prometheus Metrics

**Файл:** `tests/test_intent_and_metrics.py`

**Запуск:**
```bash
pytest tests/test_intent_and_metrics.py -v
```

**Что тестируется:**
- ✅ Emotional vs Utility intent classification (3 теста)
- ✅ Utility path routing: DIRECT/LIGHT/AGENTIC (4 теста)
- ✅ Reflection keywords → AGENTIC routing (2 теста)
- ✅ LangGraph state population (2 теста)
- ✅ Prometheus metrics incrementation (5 тестов)

**Результат:** 16/16 тестов должны проходить

**Метрики:**
- `intent_total` - Intent classifications (emotional_support, utility)
- `mode_total` - Mode routings (emotional_support, utility_direct, utility_light, utility_agentic)
- `utility_path_total` - Utility path selections (direct, light, agentic)

### Task #42713: Integration Load Testing

**Файлы:** `tests/load_test_final.py`, `tests/comprehensive_load_test.py`

**Запуск:**
```bash
# В Docker контейнере:
docker exec sophia-backend python3 /app/tests/comprehensive_load_test.py
```

**Что тестируется:**
1. ✅ Параллельные сессии (5-10 WebSocket потоков)
2. ✅ Graceful fallback механизмы
3. ✅ Захват P50/P95 латентности
4. ✅ Мониторинг метрик производительности

**Ожидаемые результаты:**
- 100% success rate на 5 параллельных сессиях
- P50 latency < 3000ms
- P95 latency < 7000ms
- Все fallback цепочки работают

---

## Troubleshooting

### Проблема: `ModuleNotFoundError: No module named 'pytest'`

**Решение:**
```bash
pip install pytest pytest-asyncio pytest-cov
```

Или используйте Docker:
```bash
docker exec sophia-backend python3 -m pytest /app/tests/...
```

### Проблема: `ModuleNotFoundError: No module named 'prometheus_client'`

**Решение:**
```bash
pip install prometheus-client
```

Или в Docker:
```bash
docker exec sophia-backend pip install prometheus-client
```

### Проблема: Load тесты падают с `fixture 'ws_url' not found`

**Причина:** Load test скрипты запущены через pytest

**Решение:** Запускайте напрямую через python:
```bash
# ❌ НЕ ПРАВИЛЬНО:
pytest tests/comprehensive_load_test.py

# ✅ ПРАВИЛЬНО:
docker exec sophia-backend python3 /app/tests/comprehensive_load_test.py
```

### Проблема: Тесты падают с Permission denied

**Решение:**
```bash
# Исправить права в контейнере:
docker exec -u root sophia-backend chmod -R 755 /app/tests
```

### Проблема: WebSocket connection refused

**Решение:**
1. Убедитесь, что контейнер запущен:
   ```bash
   docker-compose ps
   ```

2. Проверьте health check:
   ```bash
   curl http://localhost:8000/health
   ```

3. Проверьте логи:
   ```bash
   docker logs sophia-backend --tail 50
   ```

---

## CI/CD Integration

### GitHub Actions example:

```yaml
- name: Run Unit Tests
  run: |
    docker exec sophia-backend python3 -m pytest /app/tests/ \
      --ignore=/app/tests/comprehensive_load_test.py \
      --ignore=/app/tests/load_test_final.py \
      -v --tb=short

- name: Run Load Tests
  run: |
    docker exec sophia-backend python3 /app/tests/load_test_final.py
```

---

## Разработка новых тестов

### Unit тесты (pytest)

Создайте файл `tests/test_feature.py`:

```python
import pytest
from app.your_module import your_function

class TestYourFeature:
    def test_basic_case(self):
        result = your_function("input")
        assert result == "expected"

    @pytest.mark.asyncio
    async def test_async_case(self):
        result = await your_async_function()
        assert result is not None
```

Запуск:
```bash
pytest tests/test_feature.py -v
```

### Load тесты (standalone scripts)

Создайте файл `tests/load_test_feature.py` (НЕ test_*.py для pytest):

```python
#!/usr/bin/env python3
import asyncio
import websockets

async def main():
    # Your load test logic
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

Запуск:
```bash
python tests/load_test_feature.py
```

---

## Полезные команды

```bash
# Запустить только быстрые unit тесты
pytest tests/ -v -m "not slow"

# Запустить с покрытием кода
pytest tests/ --cov=app --cov-report=html

# Запустить конкретный тест по имени
pytest tests/ -k "test_emotional" -v

# Остановить на первом падении
pytest tests/ -x

# Показать print statements
pytest tests/ -v -s

# Параллельный запуск (требует pytest-xdist)
pytest tests/ -n auto
```

---

## Контакты и поддержка

При проблемах с тестами:
1. Проверьте этот README
2. Изучите конкретный LOAD_TESTING_README.md или REAL_INTEGRATION_TESTING.md
3. Проверьте логи Docker: `docker logs sophia-backend`
4. Создайте issue в GitHub с полным логом ошибки
