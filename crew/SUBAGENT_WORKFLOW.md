# SUBAGENT_WORKFLOW.md — Agon Arena Subagent Pipeline

**Версия:** 2.0  
**Последнее обновление:** 2026-03-27

---

## OVERVIEW

### Pipeline Architecture

**Базовый pipeline:**
```
PM → (ANALYST?) → DEV → (ARCH?) → TEST → OWNER_SUMMARY
```

**Важно:**
- ANALYST и ARCH — **on-demand** роли (НЕ участвуют по умолчанию)
- Вызываются **ТОЛЬКО по trigger**
- PM отвечает за решение вызывать их или нет

---

## ROLE → MODEL MAPPING

| Роль | Модель | Почему |
|------|--------|--------|
| **PM** | `modelstudio/qwen3.5-plus` | Баланс качества и скорости для координации |
| **ANALYST** | `modelstudio/qwen3.5-plus` | UX/продуктовые решения не требуют max модели |
| **DEV** | `modelstudio/qwen3-coder-plus` | Специализированная coding модель |
| **TEST** | `modelstudio/qwen3-coder-plus` | Тесты и валидация кода |
| **ARCH** | `modelstudio/qwen3-max-2026-01-23` | Сильный reasoning для системных решений |

---

## ROLES

### PM (Project Manager)

**Назначение:**
- Формулирует задачу с контекстом и требованиями
- Определяет acceptance criteria
- Координирует pipeline между ролями
- Принимает финальное решение (DONE / REWORK)

**Триггер:** Всегда (первая роль в pipeline)

---

### ANALYST (On-Demand)

**Назначение:**
- UX решения и сравнение вариантов (A/B)
- Приоритизация задач backlog
- Анализ пользовательского флоу
- Продуктовая аналитика

**Модель:** `modelstudio/qwen3.5-plus`

**Триггеры (вызывается если):**
- ✅ Есть UX задача (layout, flow, interaction)
- ✅ Есть выбор между вариантами (A/B test)
- ✅ Есть продуктовая неопределённость
- ✅ Требуется приоритизация backlog

**НЕ вызывается если:**
- ❌ Задача уже имеет чёткие требования
- ❌ Нет продуктовой неопределённости
- ❌ Изменения чисто технические (bug fix, refactoring без UX)

**Пример использования:**
```
PM → ANALYST → DEV → TEST
```
(UX задача: выбор формата scenario picker)

---

### DEV (Developer)

**Назначение:**
- Анализирует задачу от PM/ANALYST
- Предлагает план реализации
- Вносит изменения в код
- Пишет/обновляет тесты

**Модель:** `modelstudio/qwen3-coder-plus`

**Триггер:** Всегда (обязательная роль)

---

### ARCH (On-Demand)

**Назначение:**
- Архитектурные решения
- State / concurrency вопросы
- Cross-component изменения
- Сложные refactor'ы (>100 LOC)
- Внешние интеграционные риски

**Модель:** `modelstudio/qwen3-max-2026-01-23`

**Триггеры (вызывается если):**
- ✅ Изменение архитектуры системы
- ✅ Есть state management / concurrency
- ✅ Refactor > 100 строк кода
- ✅ Затронуто >1 компонента
- ✅ Есть внешний интеграционный риск
- ✅ Высокий риск регрессии

**НЕ вызывается если:**
- ❌ Простой bug fix (<50 LOC)
- ❌ Изменения в одном компоненте
- ❌ Нет архитектурных последствий
- ❌ UI/formatting изменения

**Пример использования:**
```
PM → DEV → ARCH → TEST
```
(Сложный refactor: изменение state machine duel)

---

### TEST (Tester)

**Назначение:**
- Проверяет сценарии из acceptance criteria
- Ищет регрессии в существующих тестах
- Подтверждает статус (PASS / FAIL)

**Модель:** `modelstudio/qwen3-coder-plus`

**Триггер:** Всегда (обязательная роль)

---

## PIPELINE EXAMPLES

### Example 1: UX Task (с ANALYST)

**Задача:** Выбрать формат scenario picker (AG-007)

```
PM (qwen3.5-plus)
  ↓ "Нужно улучшить UX scenario picker"
ANALYST (qwen3.5-plus)
  ↓ "Вариант A: compact list, Вариант B: split list"
  ↓ → User selected B
DEV (qwen3-coder-plus)
  ↓ "Реализовал Variant B в menu.py"
TEST (qwen3-coder-plus)
  ↓ "Telegram acceptance: PASS"
OWNER_SUMMARY
```

---

### Example 2: Simple Bug Fix (без ANALYST/ARCH)

**Задача:** Исправить опечатку в тексте кнопки

```
PM (qwen3.5-plus)
  ↓ "Опечатка в кнопке 'Завершить раунд'"
DEV (qwen3-coder-plus)
  ↓ "Исправил в keyboards/main_menu.py"
TEST (qwen3-coder-plus)
  ↓ "Тесты: PASS"
OWNER_SUMMARY
```

---

### Example 3: Complex Refactor (с ARCH)

**Задача:** Рефакторинг state machine duel (>200 LOC)

```
PM (qwen3.5-plus)
  ↓ "Рефакторинг DuelService: выделить state machine"
DEV (qwen3-coder-plus)
  ↓ "План: выделить DuelStateMachine, 250 LOC"
ARCH (qwen3-max-2026-01-23)
  ↓ "Оценка рисков: concurrency ok, migration plan ok"
TEST (qwen3-coder-plus)
  ↓ "Тесты: 6/6 PASS, регрессий нет"
OWNER_SUMMARY
```

---

### Example 4: Voice Routing Bug (без ANALYST/ARCH)

**Задача:** Исправить AG-011 (voice message ломает duel)

```
PM (qwen3.5-plus)
  ↓ "Voice message сбрасывает duel, нужен fix"
DEV (qwen3-coder-plus)
  ↓ "Fix: усилить приоритет active duel в handlers"
TEST (qwen3-coder-plus)
  ↓ "test_voice_routing.py: 6/6 PASS"
OWNER_SUMMARY
```

---

## ROLE_TRIGGERS SUMMARY

| Роль | Default | Trigger |
|------|---------|---------|
| **PM** | ✅ Всегда | Start of any task |
| **ANALYST** | ❌ Никогда | Auto: UX task, A/B choice, product uncertainty |
| **DEV** | ✅ Всегда | After PM (or PM→ANALYST) |
| **ARCH** | ❌ Никогда | Auto: Architecture change, state/concurrency, refactor >100 LOC, multi-component |
| **TEST** | ✅ Всегда | After DEV (or DEV→ARCH) |

**Note:** ANALYST и ARCH теперь определяются автоматически через ROLE_DECISION_ENGINE. PM может override вручную.

**Cost Control:**
- ANALYST: max 1 вызов на задачу (без override)
- ARCH: max 1 вызов на задачу, downgrade для single-file <100 LOC
- Логирование: ROLE_COST table в OWNER_SUMMARY

---

## DECISION TREE

```
START TASK
    │
    ▼
PM: Formulate task
    │
    ▼
[AUTO: ANALYST CHECK]
    │
    ├─ task_type == UX? → YES → ANALYST
    ├─ Contains "вариант/layout/UX/выбор/A/B"? → YES → ANALYST
    ├─ Ambiguity present? → YES → ANALYST
    └─ NO → skip ANALYST
    │
    ▼
DEV: Implement
    │
    ▼
[AUTO: ARCH CHECK]
    │
    ├─ estimated_scope > 100 LOC? → YES → ARCH
    ├─ changed_files > 1? → YES → ARCH
    ├─ Contains "refactor/архитектура/state/concurrency"? → YES → ARCH
    ├─ Integration / external risk? → YES → ARCH
    └─ NO → skip ARCH
    │
    ▼
TEST: Verify
    │
    ▼
OWNER_SUMMARY (+ ROLE_DECISION log)
```

**Manual Override:**
```
PM может переопределить:
- [OVERRIDE: force ANALYST] — несмотря на auto=no
- [OVERRIDE: force ARCH] — несмотря на auto=no
- [OVERRIDE: skip ANALYST] — несмотря на auto=yes
- [OVERRIDE: skip ARCH] — несмотря на auto=yes
```

---

## ANTI-PATTERNS

| Pattern | Problem | Fix |
|---------|---------|-----|
| ❌ ANALYST всегда в pipeline | Лишние вопросы, шум | Вызывать только при UX uncertainty |
| ❌ ARCH для простого bug fix | Waste of max model | Вызывать только при architectural risk |
| ❌ Пропускать TEST | Нет валидации | TEST обязателен всегда |
| ❌ PM → DEV без контекста | DEV не понимает задачу | PM должен дать чёткий контекст |

---

## CONFIG REQUIREMENTS

```json5
{
  agents: {
    list: [{
      id: "agonarena",
      subagents: {
        allowModelOverride: true,  // ОБЯЗАТЕЛЬНО
        allowedModels: [
          "modelstudio/qwen3.5-plus",      // PM, ANALYST
          "modelstudio/qwen3-coder-plus",  // DEV, TEST
          "modelstudio/qwen3-max-2026-01-23"  // ARCH
        ]
      }
    }]
  }
}
```

---

## ROLE_DECISION_VALIDATION

**Dry-run проверки ROLE_DECISION_ENGINE на реальных сценариях.**

---

### Example 1 — Simple UI Text Fix

**Сценарий:** "Поправить текст одной кнопки в Telegram UI"

| INPUT | Value |
|-------|-------|
| **task_type** | `bug` |
| **changed_files** | `1` (keyboards/main_menu.py) |
| **estimated_scope** | `<10 LOC` |

**Decision:**

| Роль | Решение | Почему |
|------|---------|--------|
| **ANALYST** | ❌ no | Нет UX неопределённости, задача ясная |
| **ARCH** | ❌ no | Downgrade: single-file, <100 LOC |

**Cost Control:**
- `cost_control_triggered: yes` (ARCH blocked by downgrade rule)

**Pipeline:**
```
PM → DEV → TEST
```

---

### Example 2 — Duel State Machine Refactor

**Сценарий:** "Рефакторинг state machine поединка, изменение логики раундов, таймеров и judge aggregation в 4 файлах"

| INPUT | Value |
|-------|-------|
| **task_type** | `refactor` |
| **changed_files** | `4` |
| **estimated_scope** | `>100 LOC` |

**Decision:**

| Роль | Решение | Почему |
|------|---------|--------|
| **ANALYST** | ❌ no | Нет UX неопределённости, задача техническая |
| **ARCH** | ✅ yes | Scope >100 LOC, 4 файла, state machine, refactor |

**Cost Control:**
- `cost_control_triggered: no` (ARCH разрешён по правилам)

**Pipeline:**
```
PM → DEV → ARCH → TEST
```

---

### Validation Summary

| Example | ANALYST | ARCH | Cost Triggered | Pipeline |
|---------|---------|------|----------------|----------|
| Simple UI fix | no | no | yes | PM → DEV → TEST |
| State refactor | no | yes | no | PM → DEV → ARCH → TEST |

**Вывод:** ROLE_DECISION_ENGINE корректно различает простые и сложные задачи, применяет downgrade rule для single-file задач.

---

## DEV → TEST HANDOFF (FIXED)

**Status:** ✅ FIXED (v1.7+)

**Expected Behavior:**
```
PM → DEV → [READY_FOR_TEST: yes] → [auto spawn TEST] → TEST → OWNER_SUMMARY
```

**DEV Completion Contract:**
- DEV обязан завершить ответ маркером: `READY_FOR_TEST: yes`
- Оркестрация автоматически спавнит TEST при получении маркера
- Fallback: если TEST не запущен за 5 сек → принудительный спавн

**Запрещено:**
- ❌ Ожидание ручного триггера TEST
- ❌ Завершение pipeline без TEST
- ❌ DEV без READY_FOR_TEST маркера

**Fix Applied:** AGENT_POLICY.md v1.7 — PIPELINE_HANDOFF_RULES

**Fix Tracked:** AG-016 (P0) → CLOSED

---

## TOKEN_EFFICIENCY_NOTE

**AG-015:** Analyze token efficiency across development pipeline

**План:**
1. Сначала **analysis phase** — оценить расход токенов на каждом этапе:
   - PM ↔ ANALYST ↔ DEV ↔ ARCH ↔ TEST
   - Delivery в Telegram (OWNER_SUMMARY, PM QUESTION, NEXT TASK)
   - Лишние вопросы / дублирование / verbose formatting
   - Subagent coordination overhead

2. Потом **решение** — на основе analysis:
   - Ввести отдельную роль для оптимизации?
   - Или использовать ANALYST для token efficiency reviews?
   - Или изменить pipeline формат?

**Статус:** Пока только analysis. Никакие оптимизации не применяются.

**Задача:** Добавлена в state/TODO.md (AG-015, P1, RICE: 94.5)

---

_Версия: 2.3 | Добавлены: PIPELINE_HANDOFF_RULES (DEV→TEST auto-spawn)_
