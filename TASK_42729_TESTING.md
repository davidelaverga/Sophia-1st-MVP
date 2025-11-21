# Task #42729: Mode Routing - UI Testing Guide

**Date**: November 21, 2025
**Status**: ✅ Implementation Complete - Ready for Testing
**Branch**: `feat/42729-mode-routing`

---

## 🎯 What Was Implemented

Добавлен флаг `current_mode` для интеллектуальной маршрутизации в LangGraph pipeline с 4 режимами:

1. **DIRECT** - Быстрый путь без памяти/RAG (для простых приветствий)
2. **LIGHT** - Стандартный путь с Mem0 + PromptComposer (по умолчанию)
3. **UTILITY_AGENTIC** - Сложные аналитические запросы (placeholder для reflection subgraph)
4. **EMOTIONAL_SUPPORT** - Эмоциональная поддержка (placeholder для emotional skill router)

---

## 📋 Changes Made

### 1. **GraphState Updated** (`app/langgraph_nodes.py:49`)
```python
class GraphState(TypedDict):
    ...
    current_mode: str  # NEW: DIRECT, LIGHT, UTILITY_AGENTIC, EMOTIONAL_SUPPORT
    ...
```

### 2. **ModeClassifier Node Created** (`app/langgraph_nodes.py:291`)
Новый узел после IntentAnalyzer, который определяет режим на основе:
- Intent (greeting, casual, emotional_support, crisis, knowledge)
- User emotion (joy, neutral, anxious, sad, panic, etc.)
- Query complexity (длина запроса, ключевые слова)

### 3. **ResponseGenerator Updated** (`app/langgraph_nodes.py:353`)
Добавлены методы для каждого режима:
- `_process_direct_mode()` - Skip Mem0, skip RAG, простой ответ
- `_process_light_mode()` - Include Mem0, use PromptComposer + Mistral
- `_process_utility_agentic_mode()` - Placeholder для reflection subgraph
- `_process_emotional_support_mode()` - Placeholder для emotional router

### 4. **Graph Assembly Updated** (`app/langgraph_nodes.py:1042`)
Добавлен ModeClassifier в pipeline:
```
audio_ingestor → intent_analyzer → mode_classifier → response_generator → tts_node → eval_logger
```

---

## 🧪 UI Testing Instructions

### Prerequisites
1. Убедитесь что backend запущен: `uv run python main.py` или `uv run uvicorn main:app --reload`
2. Откройте frontend или используйте Postman для API тестов
3. Проверьте что есть access к логам: `tail -f logs/sophia.log` или смотрите консоль backend

---

### Test Case 1: DIRECT Mode (Simple Greeting)

**Цель**: Проверить что простые приветствия используют быстрый путь без памяти

**Шаги**:
1. Откройте chat interface
2. Отправьте аудио или текст: **"Hello"** или **"Hi"**
3. Проверьте логи backend

**Ожидаемый результат**:
```
ModeClassifier selected mode: DIRECT
ResponseGenerator using mode: DIRECT
ResponseGenerator: DIRECT mode - fast path without memory/RAG
```

**Проверка ответа**:
- Быстрый ответ (< 1 сек)
- Простое приветствие: "Hello! How can I help you today?" или похожее
- В логах НЕ должно быть обращений к Mem0 или RAG

---

### Test Case 2: LIGHT Mode (Standard Question)

**Цель**: Проверить стандартный режим с памятью

**Шаги**:
1. Отправьте текст: **"What is DeFi?"**
2. Проверьте логи

**Ожидаемый результат**:
```
ModeClassifier selected mode: LIGHT
ResponseGenerator using mode: LIGHT
ResponseGenerator: LIGHT mode - standard path with memory
```

**Проверка ответа**:
- Ответ с использованием контекста
- В логах должны быть: "Mem0: Retrieved X memories" или "RAG context added"
- Ответ содержит информацию о DeFi

---

### Test Case 3: EMOTIONAL_SUPPORT Mode

**Цель**: Проверить режим эмоциональной поддержки

**Шаги**:
1. Отправьте текст: **"I'm feeling very anxious"** или **"I'm worried about everything"**
2. Проверьте логи

**Ожидаемый результат**:
```
IntentAnalyzer completed: intent=emotional_support (или crisis)
ModeClassifier selected mode: EMOTIONAL_SUPPORT
ResponseGenerator using mode: EMOTIONAL_SUPPORT
ResponseGenerator: EMOTIONAL_SUPPORT mode - emotional support routing
EMOTIONAL_SUPPORT: Enhanced emotional guidance with X tips
```

**Проверка ответа**:
- Эмпатичный, поддерживающий ответ
- Использование emotional guidance
- Учитывается эмоциональное состояние пользователя

---

### Test Case 4: UTILITY_AGENTIC Mode (Complex Query)

**Цель**: Проверить режим для сложных аналитических запросов

**Шаги**:
1. Отправьте длинный/сложный запрос: **"Can you explain how DeFi yield farming works compared to traditional staking mechanisms and what are the main risks involved in each approach?"**
2. Проверьте логи

**Ожидаемый результат**:
```
IntentAnalyzer completed: intent=defi_question
ModeClassifier selected mode: UTILITY_AGENTIC
ResponseGenerator using mode: UTILITY_AGENTIC
ResponseGenerator: UTILITY_AGENTIC mode - complex analysis
UTILITY_AGENTIC: Using LIGHT mode as placeholder (reflection subgraph TBD)
```

**Проверка ответа**:
- Детальный аналитический ответ
- Использование RAG контекста
- (Пока использует LIGHT mode с placeholder для reflection subgraph)

---

### Test Case 5: Mode Transition

**Цель**: Проверить что mode правильно меняется между сообщениями

**Шаги**:
1. Отправьте: **"Hello"** (ожидается DIRECT)
2. Затем: **"What is yield farming?"** (ожидается LIGHT)
3. Затем: **"I'm feeling sad"** (ожидается EMOTIONAL_SUPPORT)
4. Проверьте что каждое сообщение получает правильный mode

**Ожидаемый результат**:
- Каждое сообщение классифицируется независимо
- Mode меняется в зависимости от содержания
- Нет "залипания" на одном mode

---

## 📊 Verification Checklist

### Backend Logs
- [ ] Видны логи: `ModeClassifier selected mode: X`
- [ ] Видны логи: `ResponseGenerator using mode: X`
- [ ] DIRECT mode пропускает Mem0/RAG
- [ ] LIGHT mode включает Mem0/RAG
- [ ] EMOTIONAL_SUPPORT mode использует emotional guidance
- [ ] UTILITY_AGENTIC mode логирует placeholder

### API Response
- [ ] Response содержит правильный `intent`
- [ ] Response время отклика соответствует mode (DIRECT быстрее)
- [ ] Response качество адекватное для mode

### Edge Cases
- [ ] Пустой/очень короткий текст обрабатывается корректно
- [ ] Смешанные эмоции классифицируются правильно
- [ ] Длинные запросы (>100 слов) обрабатываются
- [ ] Русский язык поддерживается (greeting patterns включают русские слова)

---

## 🔍 Debug Tips

### Если mode не определяется правильно:

1. **Проверьте IntentAnalyzer**:
   ```
   IntentAnalyzer completed: intent=X
   ```
   Убедитесь что intent определён правильно

2. **Проверьте emotion detection**:
   ```
   user_emotion={'label': 'X', 'confidence': Y}
   ```
   Emotion влияет на выбор mode

3. **Проверьте длину запроса**:
   ```python
   # UTILITY_AGENTIC требует len(transcript.split()) > 20 или complex keywords
   ```

### Если response некорректный:

1. Проверьте что ResponseGenerator получил правильный mode
2. Проверьте fallback logs: `fallback_used` в response
3. Проверьте что Mem0/RAG доступны (если используется LIGHT mode)

---

## 🚀 Next Steps (Future Work)

### Not Implemented Yet (Placeholders):
1. **Reflection Subgraph** для UTILITY_AGENTIC mode
   - Сейчас использует enhanced LIGHT mode
   - Нужно добавить conditional branch в graph

2. **Emotional Skill Router** для EMOTIONAL_SUPPORT mode
   - Сейчас использует enhanced emotional guidance
   - Нужно добавить специализированный router

### Potential Improvements:
- ML-based mode selection вместо rule-based
- User preference override (позволить пользователю выбрать mode)
- Mode history tracking (учёт предыдущих mode в сессии)
- Performance metrics per mode (latency, quality scoring)

---

## 📝 Summary

✅ **Completed**:
- current_mode field added to GraphState
- ModeClassifier node implemented with logic for all 4 modes
- ResponseGenerator updated with mode-specific processing
- Graph assembly includes ModeClassifier in pipeline
- DIRECT mode skips Mem0 and RAG
- LIGHT mode includes Mem0 and PromptComposer
- UTILITY_AGENTIC placeholder implemented
- EMOTIONAL_SUPPORT placeholder implemented
- All initial states updated with current_mode

⏳ **Pending**:
- Unit tests (test_mode_routing.py created, needs dependencies)
- Integration tests with actual API
- UI validation with real audio/text
- Reflection subgraph implementation
- Emotional skill router implementation

---

**Implementation Date**: November 21, 2025
**Ready for Testing**: ✅ Yes
**Breaking Changes**: None (backward compatible)
