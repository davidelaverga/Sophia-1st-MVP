## REAL WebSocket Integration Load Testing

Настоящие интеграционные тесты с реальными WebSocket подключениями к серверу Sophia.

## Что тестируется (РЕАЛЬНО):

✅ **Реальные WebSocket подключения** к `/ws/voice`
✅ **Реальная отправка** PCM16 audio данных
✅ **Реальное получение** ответов от сервера
✅ **Реальная параллельная нагрузка** (5-10 одновременных сессий)
✅ **Реальные метрики** (latency, throughput, error rate)
✅ **Реальные fallback механизмы** (с мокированием внешних API)

## Методы запуска

### Метод 1: Локальный сервер (Быстро)

1. **Запустить сервер** в одном терминале:
   ```bash
   uv run python main.py
   ```

2. **Запустить тесты** в другом терминале:
   ```bash
   # Автоматический скрипт
   ./tests/run_real_load_test.sh

   # Или вручную
   python tests/test_real_websocket_integration.py
   ```

### Метод 2: Docker Compose (Изолированно)

```bash
# Запустить все сервисы и тесты
cd tests/
docker-compose -f docker-compose.test.yml up --build

# Смотреть логи
docker-compose -f docker-compose.test.yml logs -f load-tester

# Остановить
docker-compose -f docker-compose.test.yml down
```

### Метод 3: OrbStack (Рекомендуется)

1. **Запустить контейнер** в OrbStack GUI или CLI:
   ```bash
   # В OrbStack запустите sophia-backend контейнер
   # Или используйте docker-compose
   ```

2. **Запустить тесты** против контейнера:
   ```bash
   # Если контейнер на localhost:8000
   ./tests/run_real_load_test.sh

   # Если на другом хосте
   SERVER_URL=http://container-host:8000 \
   WS_URL=ws://container-host:8000 \
   ./tests/run_real_load_test.sh
   ```

### Метод 4: Pytest (CI/CD)

```bash
# Требует running server
uv run python -m pytest tests/test_real_websocket_integration.py -v -s

# С coverage
uv run python -m pytest tests/test_real_websocket_integration.py \
    --cov=app --cov-report=html -v -s
```

## Пример вывода

```
╔═══════════════════════════════════════════════════════════╗
║     REAL WebSocket Integration Load Testing              ║
╚═══════════════════════════════════════════════════════════╝

📋 Configuration:
   Server URL: http://localhost:8000
   WebSocket URL: ws://localhost:8000
   Parallel sessions: 5

🔍 Checking if server is running...
✅ Server is running at http://localhost:8000

🚀 Starting REAL load tests...

--- Test 1: Single WebSocket Connection ---
INFO:tests.test_real_websocket_integration:✓ Connected to ws://localhost:8000/ws/voice in 45.3ms
INFO:tests.test_real_websocket_integration:✓ Sent chunk 1 (16000 bytes)
INFO:tests.test_real_websocket_integration:✓ Received response: <class 'dict'>
...

--- Test 2: 5 Parallel WebSocket Sessions ---
INFO:tests.test_real_websocket_integration:🚀 Starting REAL load test with 5 parallel WebSocket sessions...
INFO:tests.test_real_websocket_integration:Session a3f2b1c8: Sent chunk 1/5 (8000 bytes)
INFO:tests.test_real_websocket_integration:Session b4c5d6e7: Sent chunk 1/5 (8000 bytes)
...

======================================================================
REAL WEBSOCKET LOAD TEST RESULTS
======================================================================
Total sessions: 5
Successful: 5
Failed: 0
Success rate: 100.0%
Total duration: 12.45s
Aggregate P50 latency: 234.5ms
Aggregate P95 latency: 456.7ms
======================================================================

Session a3f2b1c8:
  Connected: True
  Duration: 12.23s
  Audio chunks sent: 5
  Audio chunks received: 5
  Avg latency: 212.3ms
  P95 latency: 445.6ms
...

✅ Load tests completed!
```

## Архитектура тестов

### RealWebSocketClient
- Использует `websockets` библиотеку для реальных подключений
- Отправляет настоящие PCM16 audio chunks
- Получает настоящие JSON/binary ответы от сервера
- Собирает реальные метрики (latency, errors)

### RealLoadTestHarness
- Управляет 5-10 параллельными WebSocket клиентами
- Запускает клиенты одновременно через `asyncio.gather()`
- Агрегирует метрики со всех сессий
- Вычисляет P50/P95/P99 latency

### Генерация audio данных
```python
def generate_pcm16_audio(duration_ms=1000, sample_rate=16000):
    """Генерирует реальные PCM16 audio данные (тишина с шумом)"""
    # Создает настоящий PCM16 stream
    # Используется в реальных WebSocket send()
```

## Что мокируется (для контроля)

🔧 **Мокируются только внешние API** (для контроля и скорости):
- `verify_api_key()` - пропускает JWT verification
- `extract_identity_from_token()` - возвращает тестовый user_id
- `require_consent()` - пропускает consent check
- Опционально: LLM API (Mistral/Claude) для тестирования fallback
- Опционально: TTS API (Inworld/OpenAI) для тестирования fallback

❌ **НЕ мокируется** (реальное тестирование):
- WebSocket соединение - **РЕАЛЬНОЕ**
- Audio transmission - **РЕАЛЬНАЯ**
- LangGraph pipeline - **РЕАЛЬНЫЙ**
- Redis/Supabase (опционально) - **РЕАЛЬНЫЕ** или test containers
- Audio Queue Manager - **РЕАЛЬНЫЙ**
- Session Manager - **РЕАЛЬНЫЙ**

## Проверка результатов

### Успешный тест должен показать:

✅ **Connection metrics:**
- All sessions connected: `Connected: True`
- Connection time < 1000ms
- No connection errors

✅ **Transmission metrics:**
- Audio chunks sent == Audio chunks received (или близко)
- Successful send rate ≥ 95%

✅ **Latency metrics:**
- P50 latency < 500ms
- P95 latency < 2000ms
- No timeout errors

✅ **Throughput:**
- Requests per second > 5 (для 5 сессий)
- Session duration соответствует ожидаемому

### Признаки проблем:

❌ **Connection failures:**
- `Connected: False`
- Connection errors in logs
- → Проверить что сервер запущен, API key валиден

❌ **High latency:**
- P95 > 5000ms
- Timeout errors
- → Проверить нагрузку на сервер, network latency

❌ **Low throughput:**
- RPS < 2
- Many failed sends
- → Проверить server capacity, rate limits

## Troubleshooting

### Сервер не запускается
```bash
# Проверить порты
lsof -i :8000

# Проверить логи
tail -f logs/sophia.log

# Проверить env variables
cat .env
```

### WebSocket connection refused
```bash
# Проверить что сервер слушает WebSocket
curl http://localhost:8000/health

# Проверить firewall
netstat -an | grep 8000
```

### Тесты timeout
```bash
# Увеличить timeout в тестах
# Edit test_real_websocket_integration.py:
# timeout=10.0  # вместо 5.0
```

### OrbStack контейнер недоступен
```bash
# Проверить running containers
orbstack list

# Проверить порты
orbstack ps <container-id>

# Port forward если нужно
orbstack port forward <container-id> 8000:8000
```

## CI/CD Integration

```yaml
# .github/workflows/integration-tests.yml
name: Real Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Start Sophia server
        run: |
          uv run python main.py &
          sleep 10  # Wait for server to start

      - name: Run real integration tests
        run: |
          ./tests/run_real_load_test.sh

      - name: Upload test report
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: test_report.txt
```

## Следующие шаги

- [ ] Добавить stress testing (50+ параллельных сессий)
- [ ] Добавить chaos testing (random server kills)
- [ ] Интеграция с Grafana для real-time monitoring
- [ ] Performance regression tracking
- [ ] Distributed load testing (multiple test runners)

## Важные замечания

⚠️ **Эти тесты требуют running server!**
⚠️ **Не запускать на production!**
⚠️ **Используйте test environment с моками внешних API**

## Сравнение: Mock vs Real тесты

| Аспект | Mock тесты | Real тесты |
|--------|-----------|------------|
| WebSocket | ❌ Симуляция | ✅ Реальное подключение |
| Audio data | ❌ Fake bytes | ✅ Настоящий PCM16 |
| Server responses | ❌ Hardcoded | ✅ От реального сервера |
| Latency | ❌ Симулированная | ✅ Реальная измеренная |
| Fallbacks | ❌ Не тестируются | ✅ Реальные fallback chains |
| Setup | ✅ Простой | ⚠️ Требует сервер |
| Скорость | ✅ Быстро (<1s) | ⚠️ Медленно (10-30s) |
| Надежность | ⚠️ Может скрыть баги | ✅ Находит реальные проблемы |

**Вывод:** Используйте оба типа тестов:
- **Mock тесты** - для быстрой разработки и CI
- **Real тесты** - для pre-production validation и load testing
