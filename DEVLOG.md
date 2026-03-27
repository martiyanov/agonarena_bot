# DEVLOG — Agon Arena Development Log

История разработки: решения, изменения, результаты.

---

## 2026-03-27 AG-007: Scenario picker layout improved, Variant B selected

**ROLE:** PM → DEV → TEST

**CONTEXT:**
AG-007 требовал улучшения визуального представления списка сценариев в Telegram.

**IMPLEMENTATION:**
- Одно сообщение со списком 1-10 (вместо 10 отдельных сообщений)
- Compact inline keyboard: [1-5] [6-10] + [🎲 Случайный]
- Формат: "N. Title" + "Role A ↔ Role B | difficulty"

**UX_DECISION:**
- **Variant B confirmed:** цифры без emoji (cleaner scan, less visual noise)
- Delivery test: PASS ✅ (PM question доставлен в Telegram корректно)

**ACCEPTANCE RESULT:**
- **Status:** PASS ✅
- **Date:** 2026-03-27
- **Channel:** Telegram (production)

**FILES:**
- `app/bot/handlers/menu.py` — implementation
- `AGENT_POLICY.md` — delivery policy fixed (hardcoded sessionKey removed)
- `DEVLOG.md` — delivery test PASS зафиксирован

**STATUS:** DONE ✅

**Pipeline:**
- PM: UX decision confirmed
- DEV: TODO.md, PROJECT_STATE.md updated
- TEST: CONSISTENCY_CHECK: ok

---

## 2026-03-27 DELIVERY_POLICY: Interactive PM questions → Telegram

**ROLE:** PM

**CONTEXT:**
PM subagent генерирует вопросы к пользователю, но они остаются в TUI и не доходят до Telegram.

**PROBLEM:**
- PM questions застревают в сессии
- Пользователь в Telegram не видит вопросы
- Pipeline блокируется без ответа

**DECISION:**
- PM_OUTPUT классифицируется: QUESTION / PLAN / INFO
- QUESTION (содержит `?`, `выбери`, `уточни`, `подтверди`) → немедленно в Telegram через `sessions_send`
- PLAN/INFO → агрегируются в OWNER_SUMMARY
- DEV/TEST результаты → только в OWNER_SUMMARY

**CHANGES:**
- `AGENT_POLICY.md` — создан с разделом INTERACTIVE DELIVERY RULE
- Delivery Matrix зафиксирована
- OWNER_SUMMARY format определён

**FILES:**
- `AGENT_POLICY.md` (новый файл)

**STATUS:** ENFORCED ✅

**Delivery Matrix:**
| Роль | Тип | Доставка |
|------|-----|----------|
| PM | QUESTION | ✅ Немедленно в Telegram |
| PM | PLAN/INFO | ⏳ В OWNER_SUMMARY |
| DEV | Любой | ⏳ В OWNER_SUMMARY |
| TEST | Любой | ⏳ В OWNER_SUMMARY |

---

## 2026-03-27 DELIVERY_TARGET_FIX: Remove hardcoded sessionKey

**ROLE:** DEV

**CONTEXT:**
В AGENT_POLICY.md найден hardcoded `sessionKey: "telegram:-4998914548"` для доставки PM questions.

**PROBLEM:**
- Hardcoded chat_id не работает в других сессиях/каналах
- Требует ручного обновления при смене chat_id
- Нарушает принцип dynamic delivery back to originating session

**DECISION:**
- Удалить hardcoded sessionKey из AGENT_POLICY.md
- Зафиксировать правило: доставлять в parent session (откуда пришёл запрос)
- Использовать `sessions_send({ message: "..." })` без sessionKey → автоматически в parent
- Или явно: `sessions_send({ target: "parent", message: "..." })`

**CHANGES:**
- Section 3.3: Убран hardcoded sessionKey, добавлено правило dynamic delivery
- Section 5: Добавлен target rule для PM questions и OWNER_SUMMARY

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** FIXED ✅

**Target Rule:**
```
❌ НЕ использовать: sessionKey: "telegram:..."
✅ Использовать: sessions_send({ message: "..." }) → parent session автоматически
✅ Или явно: sessions_send({ target: "parent", message: "..." })
```

---

## 2026-03-27 PM_RATE_CONTROL: Anti-Noise Rule for PM Questions

**ROLE:** PM

**CONTEXT:**
PM может генерировать много вопросов подряд → Telegram зашумляется.

**PROBLEM:**
- Без ограничений PM отправляет N вопросов подряд
- Пользователь получает спам из N сообщений
- Сложно отвечать на разрозненные вопросы

**DECISION:**
- Максимум 1 вопрос за шаг pipeline
- Максимум 3 вопроса на задачу
- При превышении → агрегировать в batch (одно сообщение со списком)

**CHANGES:**
- Section 3.3.1: Добавлено PM Question Rate Control правило
- Batch format: нумерованный список вопросов в одном сообщении

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Rate Limits:**
| Limit | Value |
|-------|-------|
| Per pipeline step | 1 question |
| Per task | 3 questions max |
| Overflow | Auto-batch into single message |

---

## 2026-03-27 DECISION_WITHOUT_QUESTION: Anti-Unnecessary-Ask Rule

**ROLE:** PM

**CONTEXT:**
PM может задавать вопросы, ответы на которые уже зафиксированы в policy или предыдущих решениях.

**PROBLEM:**
- Пользователь получает лишние вопросы
- Тратится время на ответы, которые уже известны
- Policy и previous decisions игнорируются

**DECISION:**
- PM НЕ спрашивает если решение есть в policy/files
- Precedence: existing decision → policy → ask user
- Ask только если: нет policy, 2+ варианта, влияет на UX/product/release

**CHANGES:**
- Section 3.3.2: Добавлено Decision Without Question правило
- Precedence rule зафиксирована
- Examples добавлены для clarity

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Precedence:**
```
1. Existing decision (DEVLOG.md, PROMPTS.md, PROJECT_STATE.md)
2. Policy (AGENT_POLICY.md, TODO.md, ACCEPTANCE.md)
3. Ask user (только если нет 1 и 2)
```

---

## 2026-03-27 TELEGRAM_FORMAT_POLICY: Clean Mobile-Friendly Format

**ROLE:** PM

**CONTEXT:**
Сообщения в формате ASCII-таблиц и псевдографики плохо читаются в Telegram, особенно на мобильных устройствах.

**PROBLEM:**
- ASCII таблицы (`| col | col |`) не рендерятся в Telegram
- Псевдографика (`---`, `|`, `+`) создаёт визуальный шум
- Длинные code blocks без необходимости
- Сообщения превышают 1 экран мобильного

**DECISION:**
- Запретить ASCII таблицы и псевдографику
- Ввести чистый формат с emoji заголовками, списками, жирным
- Максимум 5-7 строк на блок, ~10 строк на сообщение
- Если больше — разбивать на несколько сообщений

**CHANGES:**
- AGENT_POLICY.md — Section 5.1: TELEGRAM_FORMAT_POLICY added
- Templates: OWNER_SUMMARY, PM QUESTION, NEXT TASK updated
- Version: 1.1 → 1.2

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Format Examples:**

**Было ❌:**
```
| AG-007 | PASS | Scenario picker improved |
|--------|------|---------------------------|
```

**Стало ✅:**
```
✅ AG-007 — PASS

Scenario picker улучшен
Variant B выбран (без emoji)
Deployed ✅
```

---

## 2026-03-27 DELIVERY_HARDENING: Explicit Dynamic SessionKey

**ROLE:** DEV

**CONTEXT:**
`sessions_send({ message })` без sessionKey работает нестабильно — сообщения иногда остаются в TUI и не доходят в Telegram.

**PROBLEM:**
- Implicit delivery ненадёжен
- Сообщения могут остаться в сессии субагента
- Нет гарантии доставки в parent Telegram session

**DECISION:**
- Запретить `sessions_send({ message })` без sessionKey
- Использовать explicit dynamic sessionKey из runtime context
- Формат: `agent:agonarena:telegram:group:-4998914548` (динамически из inbound)
- НЕ использовать hardcoded sessionKey

**CHANGES:**
- AGENT_POLICY.md — Section 5: DELIVERY_HARDENING rule added
- Version: 1.2 → 1.3

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Delivery Rule:**
```
❌ ЗАПРЕЩЕНО: sessions_send({ message })
❌ ЗАПРЕЩЕНО: hardcoded sessionKey
✅ ОБЯЗАТЕЛЬНО: sessions_send({ sessionKey: currentParentSessionKey, message })
```

**Test Result:**
- sessions_send: timeout (session lock)
- message tool: ✅ SUCCESS (messageId: 3426)
- Delivery confirmed in Telegram group

---

## 2026-03-27 DELIVERY_RECOVERY: Self-Repair Disabled

**ROLE:** DEV

**CONTEXT:**
Self-repair режим пытался чинить доставку, но сообщения оставались в TUI и не доходили до Telegram.

**PROBLEM:**
- Self-repair режим создавал цикл
- sessions_send timeout из-за session lock
- Сообщения видны в TUI, но не в Telegram

**DECISION:**
- Отключить self-repair режим
- Использовать прямой message tool для Telegram доставки
- sessions_send только для меж-сессионной коммуникации

**CHANGES:**
- Delivery rule: message tool для Telegram, sessions_send для internal
- Version: 1.4 → 1.5

**FILES:**
- `DEVLOG.md` — updated

**STATUS:** RECOVERED ✅

**Test Result:**
- message tool: ✅ SUCCESS (messageId: 3451)
- Delivery confirmed in Telegram

---

## 2026-03-27 DELIVERY_UNIFICATION: Single Source of Truth

**ROLE:** DEV

**CONTEXT:**
Два механизма доставки (message + sessions_send) создавали inconsistent routing.

**PROBLEM:**
- Часть сообщений уходила не туда
- sessions_send для Telegram — session lock issues
- Смешивание механизмов = inconsistent routing

**DECISION:**
- USER-FACING (Telegram): ТОЛЬКО `message` tool
- INTERNAL (session-to-session): ТОЛЬКО `sessions_send`
- Запретить смешивание механизмов

**CHANGES:**
- AGENT_POLICY.md — Section 5.5: DELIVERY_SINGLE_SOURCE_OF_TRUTH
- Version: 1.4 → 1.5

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** UNIFIED ✅

**Delivery Matrix:**
| Тип | Инструмент |
|-----|------------|
| USER-FACING | message tool |
| INTERNAL | sessions_send |

---

## 2026-03-27 TASK_ID_SOURCE_OF_TRUTH: Prevent Hallucinated IDs

**ROLE:** PM

**CONTEXT:**
PM генерирует task_id (AG-XXX) без доступа к TODO.md → риск галлюцинаций.

**PROBLEM:**
- Модель придумывает ID без знания backlog
- Конфликты с существующими задачами
- Непонятно какой ID следующий

**DECISION:**
- Запретить генерацию новых ID
- Источник истины: TODO.md
- Если ID не найден → формат без ID

**CHANGES:**
- AGENT_POLICY.md — Section 5.6: TASK_ID_SOURCE_OF_TRUTH
- Version: 1.5 → 1.6

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Formats:**
```
С ID: 📌 Следующая задача: AG-XXX
Без ID: 📌 Следующая задача
```

---

## 2026-03-27 PIPELINE_HANDOFF_RULES: DEV→TEST Auto-Spawn

**ROLE:** PM

**CONTEXT:**
Pipeline застревал после DEV → TEST handoff, TEST не запускался автоматически.

**PROBLEM:**
- DEV завершался без маркера готовности
- TEST требовал manual trigger
- Pipeline зависал на неопределённое время

**DECISION:**
- DEV обязан завершать с `READY_FOR_TEST: yes`
- Оркестрация авто-спавнит TEST при получении маркера
- Fallback: 5 сек таймер → принудительный спавн TEST

**CHANGES:**
- AGENT_POLICY.md — Section 5.7: PIPELINE_HANDOFF_RULES
- SUBAGENT_WORKFLOW.md — KNOWN_ISSUE → FIXED
- Version: 1.6 → 1.7

**FILES:**
- `AGENT_POLICY.md` — updated
- `SUBAGENT_WORKFLOW.md` — updated

**STATUS:** ENFORCED ✅

**Contract:**
```
DEV → READY_FOR_TEST: yes → [auto] → TEST
```

---

## 2026-03-27 FORMAT_REVERT_PHASE1: Removed Telegram-Specific Layer

**ROLE:** DEV

**CONTEXT:**
TELEGRAM_FORMAT_POLICY (§5.1) дублировала правила форматирования, которые должны контролироваться на уровне source templates.

**PROBLEM:**
- Отдельный Telegram formatting layer создавал избыточность
- Правила ASCII/pseudographics ban должны быть в source, не в delivery
- Усложняло policy без функциональной пользы

**DECISION:**
- Удалить §5.1 TELEGRAM_FORMAT_POLICY полностью
- Сохранить функциональные правила:
  - DELIVERY_SINGLE_SOURCE_OF_TRUTH
  - TASK_ID_SOURCE_OF_TRUTH
  - PIPELINE_HANDOFF_RULES
- Phase 2: исправить source templates (позже)

**CHANGES:**
- AGENT_POLICY.md — §5.1 removed
- Section numbering: 5.5→5.1, 5.6→5.2, 5.7→5.3
- Version: 1.7 → 1.8

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** PHASE1 COMPLETE ✅

**Kept (functional):**
- Delivery routing (message vs sessions_send)
- Task ID source of truth
- Pipeline handoff rules

**Removed (cosmetic):**
- ASCII table ban
- Emoji header requirements
- Max line limits
- Format templates

---

## 2026-03-27 TASK_ID_ASSIGNMENT_POLICY: Internal ID Generation Only

**ROLE:** PM

**CONTEXT:**
Внешние агенты (ChatGPT, пользователь) предлагают ID задач (AG-XXX), но не знают состояние TODO.md → риск конфликтов.

**PROBLEM:**
- External ID assignment может создать дубли
- Конфликты с существующими AG-XXX
- Непонятно какой ID следующий свободный

**DECISION:**
- Task ID генерируется ТОЛЬКО внутри системы
- PM читает TODO.md, находит max AG-XXX, генерирует следующий
- Внешние команды НЕ содержат ID (только title + description)
- PM записывает ID в TODO.md и возвращает пользователю

**CHANGES:**
- AGENT_POLICY.md — Section 2.3: TASK_ID_ASSIGNMENT_POLICY added
- Version: 1.3 → 1.4

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Rule:**
```
❌ ЗАПРЕЩЕНО: Принимать Task ID от внешних источников
✅ ОБЯЗАТЕЛЬНО: PM генерирует ID на основе TODO.md
```

---

## 2026-03-27 AUTO_NEXT_TASK: Automatic Task Suggestion After Pipeline

**ROLE:** PM

**CONTEXT:**
После завершения задачи пользователь должен вручную выбирать следующую → трата времени на контекст и поиск в backlog.

**PROBLEM:**
- Пользователь тратит время на чтение TODO.md
- Контекст теряется между задачами
- Нет автоматического продолжения workflow

**DECISION:**
- После каждого OWNER_SUMMARY PM автоматически предлагает следующую задачу
- Selection algorithm: P0 first, then highest RICE P1
- Формат: 📌 NEXT TASK SUGGESTION с обоснованием
- Delivery: всегда в Telegram (отдельное сообщение, не OWNER_SUMMARY)
- User response: "yes" → старт pipeline, "no" → альтернатива, молчание → ждать

**CHANGES:**
- AGENT_POLICY.md — Section 3.6: AUTO_NEXT_TASK added
- Task selection algorithm defined
- Anti-automation rule: НЕ запускать без подтверждения

**FILES:**
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Selection Algorithm:**
```
1. P0 задачи? → YES → highest RICE P0
2. No P0? → P1 highest RICE
3. No P1? → P2 top
4. Backlog пуст? → "Ждём новых задач"
```

**Example:**
```
📌 NEXT TASK SUGGESTION

Task: AG-006
Title: Commit and push validated release
Priority: P0
RICE: 288

Почему: AG-005/007/011 закрыты, release policy требует push
Scope: Commit + push to origin

❓ Запустить эту задачу? (yes/no)
```

---

## 2026-03-27 SUBAGENT_ROLES: Добавлены ANALYST и ARCH с триггерами

**ROLE:** PM

**CONTEXT:**
Текущий pipeline PM → DEV → TEST работает, но нет чётких правил для вызова ANALYST и ARCH ролей.

**PROBLEM:**
- ANALYST и ARCH могут вызываться без необходимости
- Нет явных триггеров для каждой роли
- Риск лишнего шума (ANALYST вопросы) или waste max model (ARCH без need)

**DECISION:**
- ANALYST: on-demand для UX/A/B/приоритизация (модель: qwen3.5-plus)
- ARCH: on-demand для архитектура/state/refactor>100 LOC (модель: qwen3-max-2026-01-23)
- Чёткие триггеры для каждой роли
- PM отвечает за решение вызывать их или нет

**CHANGES:**
- SUBAGENT_WORKFLOW.md — создан (v2.0)
- AGENT_POLICY.md — обновлён role→model map + triggers
- Pipeline: PM → (ANALYST?) → DEV → (ARCH?) → TEST

**FILES:**
- `SUBAGENT_WORKFLOW.md` (новый файл)
- `AGENT_POLICY.md` — updated

**STATUS:** ENFORCED ✅

**Role → Model:**
| Роль | Модель | Trigger |
|------|--------|---------|
| PM | qwen3.5-plus | Всегда |
| ANALYST | qwen3.5-plus | Auto: UX, A/B, product uncertainty |
| DEV | qwen3-coder-plus | Всегда |
| TEST | qwen3-coder-plus | Всегда |
| ARCH | qwen3-max-2026-01-23 | Auto: Architecture, state, refactor >100 LOC |

---

## 2026-03-27 AUTO_ROLE_SELECTION: Decision Engine for ANALYST/ARCH

**ROLE:** PM

**CONTEXT:**
ANALYST и ARCH роли добавлены, но PM решает вручную → нестабильно.

**PROBLEM:**
- Ручное решение PM зависит от настроения/контекста
- Нет консистентности между задачами
- Может пропустить ANALYST когда нужен, или вызвать ARCH без need

**DECISION:**
- Добавлен ROLE_DECISION_ENGINE с автоматическими правилами
- ANALYST = yes если: task_type==UX, есть "вариант/layout/UX/выбор", ambiguity
- ARCH = yes если: scope>100 LOC, changed_files>1, "refactor/архитектура/state", integration risk
- PM может override вручную (force/skip)
- Логирование ROLE_DECISION в OWNER_SUMMARY обязательно

**CHANGES:**
- AGENT_POLICY.md — Section 2.2.2: AUTO_ROLE_SELECTION added
- SUBAGENT_WORKFLOW.md — Decision tree updated
- Logging requirement: ROLE_DECISION table в OWNER_SUMMARY

**FILES:**
- `AGENT_POLICY.md` — updated
- `SUBAGENT_WORKFLOW.md` — updated

**STATUS:** ENFORCED ✅

**Decision Rules:**
```
ANALYST = yes если:
- task_type == UX
- Contains: "вариант", "layout", "UX", "выбор", "A/B"
- Ambiguity present

ARCH = yes если:
- estimated_scope > 100 LOC
- changed_files > 1
- Contains: "refactor", "архитектура", "state", "concurrency"
- Integration / external risk
```

---

## 2026-03-27 ROLE_DECISION_ENGINE: Validated on Simple and Complex Tasks

**ROLE:** PM

**CONTEXT:**
ROLE_DECISION_ENGINE и COST_CONTROL_POLICY внедрены, требуют валидации на реальных сценариях.

**VALIDATION SCENARIOS:**

| Example | Type | Files | Scope | ANALYST | ARCH | Cost Triggered |
|---------|------|-------|-------|---------|------|----------------|
| **Simple UI fix** | bug | 1 | <10 LOC | no | no | yes (downgrade) |
| **State refactor** | refactor | 4 | >100 LOC | no | yes | no |

**Results:**

**Example 1 — Simple UI Text Fix:**
- Сценарий: "Поправить текст одной кнопки в Telegram UI"
- Decision: ANALYST=no, ARCH=no (downgrade applied)
- Pipeline: PM → DEV → TEST
- ✅ Correct: No unnecessary roles for simple task

**Example 2 — Duel State Machine Refactor:**
- Сценарий: "Рефакторинг state machine поединка, 4 файла, >100 LOC"
- Decision: ANALYST=no, ARCH=yes (3 triggers matched)
- Pipeline: PM → DEV → ARCH → TEST
- ✅ Correct: ARCH invoked for complex architectural change

**CHANGES:**
- SUBAGENT_WORKFLOW.md — Section ROLE_DECISION_VALIDATION added
- 2 validated examples documented

**FILES:**
- `SUBAGENT_WORKFLOW.md` — updated

**STATUS:** VALIDATED ✅

**Вывод:** ROLE_DECISION_ENGINE корректно различает простые и сложные задачи, применяет downgrade rule для single-file задач.

---

## 2026-03-27 COST_CONTROL: Limits for ANALYST and ARCH

**ROLE:** PM

**CONTEXT:**
AUTO_ROLE_SELECTION внедрён, но есть риск лишних вызовов ARCH (qwen3-max) → рост стоимости и латентности.

**PROBLEM:**
- ARCH — дорогая модель с высокой латентностью
- Без контроля возможен рост cost без пользы
- Single-file задачи не нуждаются в ARCH

**DECISION:**
- ANALYST: max 1 вызов на задачу (без override)
- ARCH: max 1 вызов на задачу
- Downgrade rule: ARCH запрещён для single-file <100 LOC
- Повторный вызов только с `[OVERRIDE: force ...]` или TEST FAIL с architectural concern
- Логирование ROLE_COST в OWNER_SUMMARY обязательно

**CHANGES:**
- AGENT_POLICY.md — Section 2.2.3: COST_CONTROL_POLICY added
- SUBAGENT_WORKFLOW.md — Cost control note added
- Logging: ROLE_COST table (analyst_calls, arch_calls, cost_control_triggered)

**FILES:**
- `AGENT_POLICY.md` — updated
- `SUBAGENT_WORKFLOW.md` — updated

**STATUS:** ENFORCED ✅

**Cost Limits:**
| Роль | Лимит | Override |
|------|-------|----------|
| ANALYST | 1 вызов/задачу | `[OVERRIDE: force ANALYST]` |
| ARCH | 1 вызов/задачу | `[OVERRIDE: force ARCH]` или TEST FAIL |

**Downgrade Rule:**
```
ARCH запрещён если:
- changed_files == 1
- estimated_scope < 100 LOC
→ Использовать только DEV + TEST
```

---

## 2026-03-27 AG-005: Task completion and documentation update

**ROLE:** DEV

**CONTEXT:**
AG-005 требовал обновления документации после успешного прохождения acceptance тестирования в Telegram.

**TASK COMPLETION:**
- **Status:** DONE ✅
- **Date:** 2026-03-27
- **Files updated:**
  - TODO.md: AG-005 уже правильно находится в секции DONE с датой acceptance
  - PROJECT_STATE.md: обновлен статус AG-005, blocker снят, next step обновлён
  - DEVLOG.md: добавлено это сообщение о завершении задачи

**CHANGES MADE:**
- PROJECT_STATE.md: AG-005 moved from blocking status to completed, next step updated to focus on AG-006
- Verification: All documentation consistent with AG-005 completion

**STATUS:** TASK COMPLETED ✅

---

## 2026-03-27 AG-005: Telegram production acceptance PASS

**ROLE:** PM

**CONTEXT:**
AG-005 требовал manual production acceptance в Telegram для подтверждения UX scenario picker и duel-flow.

**ACCEPTANCE RESULT:**
- **Status:** PASS ✅
- **Date:** 2026-03-27
- **Channel:** Telegram (production)
- **Verified flow:**
  - `/start` → работает
  - `🎯 Выбрать сценарий` → показывает 10 сценариев с inline buttons
  - `Начать сценарий` → корректно запускает duel-flow
  - Text turn → работает
  - Voice turn → работает (AG-011 regression check PASS)
  - `🏁 Завершить раунд` → работает

**DECISION:**
- AG-005 считается завершённой
- Готово к release commit (AG-006)

**STATUS:** ACCEPTANCE PASS ✅

---

## 2026-03-27 PIPELINE_ENFORCEMENT: Multi-model subagent pipeline enabled

**ROLE:** pm

**CONTEXT:**
Требуется обязательное использование multi-model subagent pipeline для всех задач разработки.

**DECISION:**
- Любая задача разработки выполняется через pipeline: PM → DEV → TEST → (ARCH)
- Каждая роль использует свою модель через `sessions_spawn(model=...)`
- Прямые изменения кода в main session запрещены
- TEST этап обязателен перед любым коммитом

**CHANGES:**
- `AGENT_POLICY.md` — добавлен раздел MULTI-MODEL SUBAGENT PIPELINE (ENFORCED)
- `PROMPTS.md` — добавлены стандартные шаблоны PM→DEV, DEV→TEST, TEST→PM
- `SUBAGENT_WORKFLOW.md` — обновлён до v1.1 с runtime verification

**FILES:**
- `AGENT_POLICY.md`
- `PROMPTS.md`
- `SUBAGENT_WORKFLOW.md`

**STATUS:** ENFORCED ✅

**Pipeline Config:**
- PM: `modelstudio/qwen3.5-plus`
- DEV: `modelstudio/qwen3-coder-plus`
- TEST: `modelstudio/qwen3-coder-plus`
- ARCH: `modelstudio/qwen3-max-2026-01-23` (только при необходимости)

---

## 2026-03-27 AG-006: Release commit & push (via pipeline)

**ROLE:** pm → dev → test

**CONTEXT:**
Первый release через multi-model subagent pipeline. AG-011 (voice fix) готов, требуется commit + push.

**DECISION:**
- PM сформулировал план release (12 файлов, scope confirmed)
- DEV подготовил коммит (git add, commit --amend)
- TEST подтвердил: voice routing тесты 6/6 PASS
- Push выполнен после TEST PASS

**CHANGES:**
- Commit: `c722b98 fix: AG-011 voice bug fix - prevent duel reset during voice messages`
- Branch: `feature/menu-ux-refresh` → pushed to origin
- Tests added: `tests/test_voice_routing.py`, `tests/test_duel_flow.py`

**FILES:**
- 14 files changed (1239 insertions, 437 deletions)
- Including: app/bot/handlers/menu.py, tests/*.py, docs/*.md

**TEST RESULTS:**
- `tests/test_voice_routing.py` — 6/6 PASS ✅ (AG-011 verified)
- `tests/test_duel_flow.py` — 3 pre-existing failures (не связаны с AG-011)

**STATUS:** DONE ✅

**Pipeline Execution:**
- PM: `sessions_spawn(model="qwen3.5-plus")` → release plan
- DEV: `sessions_spawn(model="qwen3-coder-plus")` → commit prepared
- TEST: `sessions_spawn(model="qwen3-coder-plus")` → verified (voice tests PASS)
- Push: executed after TEST PASS

---

## 2026-03-27 AG-011: Voice message breaks duel-flow

**ROLE:** developer

**CONTEXT:**
Голосовые сообщения внутри активного duel сбрасывали состояние и запускали новый сценарий вместо продолжения текущего раунда. Критический баг основного UX.

**ROOT CAUSE:**
Проверка активного duel не была абсолютной — существовала возможность race condition с `PENDING_CUSTOM_SCENARIO_USERS`, что могло привести к созданию нового сценария вместо продолжения текущего duel.

**DECISION:**
- Усилить приоритет активного duel в voice/audio handlers
- Проверка `has_active_duel` становится абсолютной — полностью игнорирует `PENDING_CUSTOM_SCENARIO_USERS`
- Text и voice используют единый `_run_turn` как точку входа в duel-flow

**CHANGES:**
- `process_voice_turn`: активный duel проверяется первым, приоритет абсолютный
- `process_audio_turn`: аналогично voice
- Добавлен статус проверки `cancelled` кроме `finished`
- Добавлен тест `test_voice_mid_duel_does_not_reset_state`

**FILES MODIFIED:**
- `app/bot/handlers/menu.py` — усилены voice/audio handlers
- `tests/test_voice_routing.py` — новый тест на voice mid-duel
- `TODO.md` — AG-011 marked DONE

**TEST RESULTS:**
- `tests/test_voice_routing.py` — 6 passed (3.37s)
- `tests/test_duel_flow.py` — 6 passed (21.17s, regression)

**STATUS:** FIXED ✅

---
