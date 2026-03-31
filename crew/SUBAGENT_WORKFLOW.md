# SUBAGENT_WORKFLOW.md — Agon Arena Subagent Pipeline

**Версия:** 2.0  
**Последнее обновление:** 2026-03-27

---

## OVERVIEW

### Pipeline Architecture

**Базовый pipeline:**
```
PM → (ANALYST?) → DEV → MANUAL TEST → (ARCH?) → TEST → OWNER_SUMMARY
```

**Важно:**
- ANALYST и ARCH — **on-demand** роли (НЕ участвуют по умолчанию)
- Вызываются **ТОЛЬКО по trigger**
- PM отвечает за решение вызывать их или нет
- **MANUAL TEST** — **обязательный этап** после DEV (до TEST)

### Почему MANUAL TEST раньше?

**Было:** DEV → TEST → MANUAL TEST  
**Стало:** DEV → MANUAL TEST → TEST

**Преимущества:**
- Баги находятся раньше (до написания unit тестов)
- TEST субагент не тратит время на заведомо сломанный код
- Быстрее feedback для DEV
- **Эффект:** -30-50% времени задачи

**MANUAL TEST чек-лист:**
- [ ] Основной flow работает
- [ ] UI кнопки корректны
- [ ] Нет критических багов
- [ ] Готово к TEST (unit/automation)

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
- **Проверяет новые задачи на пересечение с текущими**

**Триггер:** Всегда (первая роль в pipeline)

**PM Checklist (при получении новой задачи):**
1. [ ] Прочитать `state/task-tracker.json` (активные задачи)
2. [ ] Прочитать `state/bug-registry.md` (известные баги)
3. [ ] Прочитать `state/TODO.md` (backlog)
4. [ ] Проверить пересечения с текущими задачами
5. [ ] Если пересечение есть → спросить пользователя как разрешить конфликт
6. [ ] Сохранить контекст текущих задач

**Проверка пересечений:**
- **По файлам:** Затрагивает ли те же файлы?
- **По функционалу:** Один ли это компонент/фича?
- **По багам:** Связано ли с известными багами?
- **По контексту:** Требует ли тех же знаний/доступа?

**Если найдено пересечение:**
```
⚠️ Найдено пересечение с задачей AG-XXX

Новая задача: [описание]
Текущая задача: AG-XXX [описание]

Пересечение: [файлы/функционал/баги]

Вопрос: Как разрешить конфликт?
1. Объединить задачи (сделать одной задачей)
2. Приоритизировать (сначала AG-XXX, потом новая)
3. Разделить (независимая реализация)
4. Отложить новую задачу

Жду решения...
```

**Контекст задач:**
- Сохранять связи между задачами в `state/task-tracker.json`
- Добавлять `relatedTasks: ["AG-XXX"]` при пересечении
- Вести `state/task-context.md` с общим контекстом

---

### ANALYST / UX-ANALYST (On-Demand)

**Назначение:**
- UX решения и сравнение вариантов (A/B)
- Приоритизация задач backlog
- Анализ пользовательского флоу
- Продуктовая аналитика
- **UX-спецификации для изменений в UI/кнопках/навигации**
- **Проверка новых задач на пересечение с текущими**

**Модель:** `modelstudio/qwen3.5-plus`

**Триггеры (вызывается если):**
- ✅ Есть UX задача (layout, flow, interaction)
- ✅ Есть выбор между вариантами (A/B test)
- ✅ Есть продуктовая неопределённость
- ✅ Требуется приоритизация backlog
- ✅ **Изменения в кнопках, меню, навигации**
- ✅ **Изменения в пользовательских сценариях (user flow)**
- ✅ **PM попросил проверить пересечения задач**

**НЕ вызывается если:**
- ❌ Задача уже имеет чёткие требования
- ❌ Нет продуктовой неопределённости
- ❌ Изменения чисто технические (bug fix, refactoring без UX)

**ANALYST Checklist (проверка пересечений и дублирования):**
1. [ ] Прочитать новую задачу/баг
2. [ ] Прочитать активные задачи (`state/task-tracker.json`)
3. [ ] Прочитать bug-registry (`state/bug-registry.md`)
4. [ ] Прочитать backlog (`state/TODO.md`)
5. [ ] **Проверить на дублирование:**
   - Такой же баг уже есть?
   - Такая же задача в работе/бэклоге?
   - Похожий функционал уже реализуется?
6. [ ] Найти пересечения (файлы, функционал, контекст)
7. [ ] Оценить риски конфликта
8. [ ] Предложить вариант разрешения

**Если найдено дублирование:**
```
⚠️ Возможное дублирование!

Новая задача: [описание]
Существующая: AG-XXX [описание]

Совпадение: [в чём похоже]

Рекомендация:
1. Объединить (одна задача вместо двух)
2. Закрыть как дубликат
3. Уточнить различия (если есть)
``` (объединить/приоритизировать/разделить)

**Как вызывать:**
```python
sessions_spawn(
    task="UX-анализ: [описание задачи]",
    agentId="agonarena",
    runtime="subagent",
    mode="run"
)
```

**Пример использования:**
```
PM → ANALYST → DEV → TEST
```
(UX задача: выбор формата scenario picker)

(UX задача: перенос кнопки из нижнего меню в inline)

---

### DEV (Developer)

**Назначение:**
- Анализирует задачу от PM/ANALYST
- Предлагает план реализации
- Вносит изменения в код
- Пишет/обновляет тесты
- **Самопроверка перед MANUAL TEST** (чек-лист ниже)

**Модель:** `modelstudio/qwen3-coder-plus`

**Триггер:** Всегда (обязательная роль)

**DEV Checklist (перед передачей на MANUAL TEST):**
- [ ] Код работает локально
- [ ] Unit тесты написаны/обновлены
- [ ] Нет очевидных багов (проверил сам)
- [ ] Изменения задокументированы (state/TODO.md)
- [ ] **DEPLOY:** Запустить `./scripts/deploy.sh` для деплоя в Docker

---

### ARCH (On-Demand)

**Назначение:**
- Архитектурные решения
- State / concurrency вопросы
- Cross-component изменения
- Сложные refactor'ы (>100 LOC)
- Внешние интеграционные риски
- **Проверка изменений в UX/UI на предмет влияния на архитектуру**

**Модель:** `modelstudio/qwen3-max-2026-01-23`

**Триггеры (вызывается если):**
- ✅ Изменение архитектуры системы
- ✅ Есть state management / concurrency
- ✅ Refactor > 100 строк кода
- ✅ Затронуто >1 компонента
- ✅ Есть внешний интеграционный риск
- ✅ Высокий риск регрессии
- ✅ **UX-изменения влияют на механику/состояния/flow**

**НЕ вызывается если:**
- ❌ Простой bug fix (<50 LOC)
- ❌ Изменения в одном компоненте
- ❌ Нет архитектурных последствий
- ❌ UI/formatting изменения (без влияния на flow)

**Как вызывать:**
```python
sessions_spawn(
    task="Архитектурный анализ: [описание задачи]",
    agentId="agonarena",
    runtime="subagent",
    mode="run"
)
```

**Пример использования:**
```
PM → DEV → ARCH → TEST
```
(Сложный refactor: изменение state machine duel)

(UX + Arch: перенос кнопки с изменением callback flow)

---

### CODE_REVIEW (On-Demand)

**Назначение:**
- Проверка кода перед TEST
- Поиск багов, anti-patterns, уязвимостей
- Рекомендации по улучшению
- **Gate перед TEST** (не пропускать баги дальше)

**Модель:** `modelstudio/qwen3-coder-plus` или `modelstudio/qwen3-max-2026-01-23` (для сложного кода)

**Триггеры (вызывается если):**
- ✅ Изменения >100 LOC
- ✅ Критичный функционал (платёжки, безопасность)
- ✅ Рефакторинг сложной логики
- ✅ DEV попросил review

**НЕ вызывается если:**
- ❌ Простой bug fix (<50 LOC)
- ❌ UI/formatting изменения
- ❌ MANUALLY TESTED и багов нет

**Пример использования:**
```
PM → DEV → CODE_REVIEW → TEST
```

---

### TEST (Tester)

**Назначение:**
- Проверяет сценарии из acceptance criteria
- Ищет регрессии в существующих тестах
- Подтверждает статус (PASS / FAIL)
- **Запускается только после MANUAL TEST без критических багов**

**Модель:** `modelstudio/qwen3-coder-plus`

**Триггер:** Всегда (обязательная роль)

**Входные критерии для TEST:**
- [ ] MANUAL TEST завершён (без критических багов)
- [ ] DEV checklist выполнен
- [ ] CODE_REVIEW пройден (если требуется)

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
    ├─ Contains "кнопки/меню/навигация"? → YES → ANALYST
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
    ├─ Contains "UX влияет на flow/mechanics"? → YES → ARCH
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

## TASK TRACKING & MONITORING

**Механизм против зависания задач:**

### Task Tracker

Файл: `state/task-tracker.json`

**Структура:**
```json
{
  "activeTasks": [...],
  "completedTasks": [...],
  "config": {
    "checkIntervalMinutes": 10,
    "warnAfterMinutes": 30,
    "escalateAfterMinutes": 60
  }
}
```

**Статусы задач:**
- `active` — в работе (субагент запущен)
- `ready_for_manual_test` — готово к ручному тестированию
- `blocked` — ждёт внешнего действия
- `done` — завершено

### Task Monitor

Скрипт: `scripts/task-monitor.py`

**Запускается:** Каждые 10 минут (cron)

**Логика:**
1. Проверяет `activeTasks` и `completedTasks` со статусом `ready_for_manual_test`
2. Если задача ждёт >30 мин → warning в лог
3. Если задача ждёт >60 мин → эскалация пользователю

**Cron job:** "Task Monitor — проверка зависших задач"

### Process Analyzer

Скрипт: `scripts/process-analyzer.py`

**Запускается:** Раз в день в 21:00 (cron, Europe/Berlin)

**Анализирует:**
1. Историю задач (task-tracker.json)
2. Daily notes (memory/YYYY-MM-DD.md)
3. Process analysis (state/process-analysis.md)

**Выдаёт:**
- Метрики за день (bug rate, manual test fail rate, bottlenecks)
- Паттерны (частые проблемы, повторяющиеся задачи)
- Рекомендации по оптимизации процесса
- Итоги дня (завершённые задачи, проблемы, план на завтра)

**Cron job:** "Process Analysis — ежедневный анализ (конец дня)"

### PM Обязанности

**После завершения субагента:**
1. Обновить `state/task-tracker.json`
2. Если следующий этап — ручной тест → пометить `waitingFor: "user"`
3. Если следующий этап — другой субагент → вызвать сразу

**Не ждать вопроса пользователя!** Проактивно:
- Отчитываться о завершении этапа
- Вызывать следующий этап сразу
- Помечать если ждёшь пользователя

**Ежедневный анализ (21:00):**
1. Process Analyzer автоматически запустится
2. Даст сводку за день
3. Рекомендации на завтра

---

## SUBAGENT SPAWN MECHANISM

**Как вызывать субагентов для ролей ANALYST/ARCH/UX:**

Все специализированные роли (ANALYST, UX-ANALYST, ARCH) вызываются через `sessions_spawn` с `runtime="subagent"`.

### Пример: Вызов UX-аналитика

```python
from openclaw.tool_client import ToolClient

client = ToolClient()

# UX-анализ задачи
await client.call_tool("sessions_spawn", {
    "task": "UX-анализ: перенос кнопки 'Завершить раунд' из нижнего меню в inline-кнопки",
    "agentId": "agonarena",
    "runtime": "subagent",
    "mode": "run",
    "label": "ux-analyst-inline-button"
})
```

### Пример: Вызов архитектора

```python
# Архитектурный анализ
await client.call_tool("sessions_spawn", {
    "task": "Архитектурный анализ: изменение callback flow для inline-кнопки завершения раунда",
    "agentId": "agonarena",
    "runtime": "subagent",
    "mode": "run",
    "label": "arch-callback-flow"
})
```

### Параметры sessions_spawn

| Параметр | Значение | Описание |
|----------|----------|----------|
| `task` | string | Задача для субагента (подробное описание) |
| `agentId` | "agonarena" | ID агента (из agents_list) |
| `runtime` | "subagent" | Тип рантайма |
| `mode` | "run" | Одноразовое выполнение |
| `label` | string | Метка для идентификации сессии |

### Ожидание результата

После спавна субагента:
1. Субагент работает изолированно
2. По завершении — авто-анонс в родительскую сессию
3. Результат доступен через `sessions_list` или `subagents action=list`

**Важно:** Не poll'ить `subagents list` в цикле. Проверять статус по-demand или ждать анонса.

---

## AGREEMENT: UX/ARCH REVIEW BEFORE IMPLEMENTATION

**Дата:** 2026-03-29  
**Задача:** Inline-кнопка "Завершить раунд" (AG-017)

**Договорённости:**

1. **UX-изменения требуют ревью**
   - Изменения в кнопках, меню, навигации → **обязательно UX-аналитик**
   - Изменения в user flow → **обязательно UX-аналитик**
   - Изменения в механике → **UX + Архитектор**

2. **Порядок вызова**
   ```
   PM → UX-ANALYST → [ARCH если нужно] → DEV → TEST
   ```

3. **Как вызывать**
   - UX-аналитик: `sessions_spawn(runtime="subagent", task="UX-анализ: ...")`
   - Архитектор: `sessions_spawn(runtime="subagent", task="Архитектурный анализ: ...")`
   - Через ChatGPT-5.4: скопировать промпт из `tasks/ux-analyst-prompt.md`

4. **Фиксация результата**
   - Ответ UX/ARCH сохранять в `tasks/ux-analyst-response.md` или `tasks/arch-response.md`
   - После согласования → переход к реализации (DEV)

**Это правило добавлено в политику на основании задачи AG-017.**

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
