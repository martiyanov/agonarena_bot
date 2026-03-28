# AGENT_POLICY.md — Agon Arena Development Policy

**ЭТОТ ФАЙЛ — SOURCE OF TRUTH** для разработки в проекте Agon Arena.

---

## 1. Обязательные правила

### 1.1 Перед началом любой задачи:
- Прочитать этот файл
- Следовать ему как source of truth
- Игнорировать правила из старых сообщений, если они противоречат этому файлу

### 1.2 Приоритет: китайский стек (ModelStudio)

| Роль | Модель | Когда |
|------|--------|-------|
| **PM** | `modelstudio/qwen3.5-plus` | Всегда (координация) |
| **ANALYST** | `modelstudio/qwen3.5-plus` | On-demand (UX, A/B, приоритизация) |
| **DEV** | `modelstudio/qwen3-coder-plus` | Всегда (реализация) |
| **TEST** | `modelstudio/qwen3-coder-plus` | Всегда (валидация) |
| **ARCH** | `modelstudio/qwen3-max-2026-01-23` | On-demand (архитектура, state, refactor) |

### 1.3 OpenAI policy
- ❌ Не использовать OpenAI по умолчанию
- ⚠️ `gpt-5.4` — только как резерв по явной команде
- ❌ `gpt-4o-mini` — не использовать

---

## 2. MULTI-MODEL SUBAGENT PIPELINE (ENFORCED)

### 2.1 Обязательный pipeline для любой задачи разработки

**Любая задача разработки выполняется через pipeline:**
```
PM → DEV → TEST → (ARCH при необходимости) → OWNER_SUMMARY
```

**Механизм:** `sessions_spawn` с `model` override

### 2.2 Role → Model Mapping (обязательно)

| Роль | Модель | Когда |
|------|--------|-------|
| **PM** | `modelstudio/qwen3.5-plus` | Всегда (координация) |
| **ANALYST** | `modelstudio/qwen3.5-plus` | On-demand (UX, A/B, приоритизация) |
| **DEV** | `modelstudio/qwen3-coder-plus` | Всегда (реализация) |
| **TEST** | `modelstudio/qwen3-coder-plus` | Всегда (валидация) |
| **ARCH** | `modelstudio/qwen3-max-2026-01-23` | On-demand (архитектура, state, refactor) |

---

### 2.3 TASK_ID_ASSIGNMENT_POLICY

**Проблема:** Внешние агенты (ChatGPT, пользователь) предлагают ID задач (AG-XXX), но не знают текущее состояние state/TODO.md → риск конфликтов и дублей.

**Решение:** Генерация Task ID происходит ТОЛЬКО внутри системы.

**Правило:**
```
❌ ЗАПРЕЩЕНО: Принимать Task ID от внешних источников
✅ ОБЯЗАТЕЛЬНО: PM генерирует ID на основе state/TODO.md
```

**PM обязан:**
1. Прочитать state/TODO.md перед началом задачи
2. Найти следующий свободный AG-XXX (max + 1)
3. Записать новый ID в state/TODO.md
4. Вернуть ID в ответе пользователю

**Внешние команды (от владельца):**
- НЕ содержат ID
- Содержат только title и описание
- Пример: "Добавь кнопку обратной связи" (без AG-XXX)

**Пример:**
```
User: "Нужно добавить кнопку обратной связи"
PM: 
  1. Читает state/TODO.md → последний AG-016
  2. Генерирует AG-017
  3. Записывает в state/TODO.md
  4. Отвечает: "✅ AG-017 добавлена: Кнопка обратной связи"
```

**Конфликты:**
- Если внешний агент предложил AG-XXX → PM игнорирует, генерирует свой
- Если дубль обнаружен → PM сообщает и предлагает альтернативный ID

### 2.2.1 Role Triggers

**ANALYST вызывается если:**
- ✅ Есть UX задача (layout, flow, interaction)
- ✅ Есть выбор между вариантами (A/B test)
- ✅ Есть продуктовая неопределённость
- ✅ Требуется приоритизация backlog

**ARCH вызывается если:**
- ✅ Изменение архитектуры системы
- ✅ Есть state management / concurrency
- ✅ Refactor > 100 строк кода
- ✅ Затронуто >1 компонента
- ✅ Есть внешний интеграционный риск
- ✅ Высокий риск регрессии

**Важно:**
- ❌ ANALYST и ARCH **НЕ** участвуют по умолчанию
- ❌ Нельзя вызывать без trigger
- ✅ PM отвечает за решение вызывать их или нет

---

### 2.2.2 AUTO_ROLE_SELECTION (Decision Engine)

**Проблема:** PM решает вручную → нестабильно, зависит от настроения PM.

**Решение:** Автоматическое принятие решения на основе правил.

#### ROLE_DECISION_ENGINE

**INPUT:**
| Поле | Описание |
|------|----------|
| `task_description` | Текст задачи от пользователя |
| `changed_files` | Список файлов (если известен) |
| `estimated_scope` | Примерный объём изменений (LOC) |
| `task_type` | `bug` / `UX` / `feature` / `refactor` |

**OUTPUT:**
| Поле | Описание |
|------|----------|
| `use_analyst` | yes/no + причина |
| `use_arch` | yes/no + причина |

---

#### ANALYST = yes если (любое из):

| Условие | Пример |
|---------|--------|
| `task_type == UX` | "Улучшить UX scenario picker" |
| Есть слова: `"вариант"`, `"layout"`, `"UX"`, `"выбор"`, `"A/B"` | "Выбрать между вариантом A и B" |
| Есть ambiguity в задаче | "Неясно, как лучше сделать" |
| Требуется продуктовое решение | "Нужно решение от владельца продукта" |

---

#### ARCH = yes если (любое из):

| Условие | Пример |
|---------|--------|
| `estimated_scope > 100 LOC` | "Рефакторинг ~200 строк" |
| `changed_files > 1` | Затронуты несколько файлов/компонентов |
| Есть слова: `"refactor"`, `"архитектура"`, `"state"`, `"concurrency"` | "Изменить state machine" |
| Integration / external dependency | "Интеграция с внешним API" |
| Высокий риск регрессии | "Изменение ядра системы" |

---

#### Priority Order

```
1. Сначала ANALYST (если UX неопределённость)
2. Потом DEV (реализация)
3. Потом ARCH (если архитектурный риск)
4. Потом TEST (валидация)
```

**Pipeline с auto-selection:**
```
PM → [AUTO: ANALYST?] → DEV → [AUTO: ARCH?] → TEST → OWNER_SUMMARY
```

---

#### Manual Override

PM может вручную переопределить автоматическое решение:

| Override | Когда |
|----------|-------|
| `force ANALYST` | PM хочет второе мнение по UX |
| `force ARCH` | PM чувствует риск, но правила не сработали |
| `skip ANALYST` | UX уже зафиксирован в policy |
| `skip ARCH` | Рефакторинг простой, несмотря на scope |

**Формат override:**
```
[OVERRIDE: skip ANALYST — UX уже зафиксирован в AGENT_POLICY.md]
[OVERRIDE: force ARCH — высокий риск регрессии]
```

---

#### Logging Requirement

Каждый pipeline должен писать в начало OWNER_SUMMARY:

```markdown
### ROLE_DECISION
- ANALYST: yes/no — <причина>
- ARCH: yes/no — <причина>
```

**Пример:**
```markdown
### ROLE_DECISION
- ANALYST: yes — UX task, выбор между variant A/B
- ARCH: no — изменения в одном компоненте, <50 LOC
```

---

### 2.2.3 COST_CONTROL_POLICY

**Проблема:** ARCH (qwen3-max) — дорогая модель с высокой латентностью. Риск лишних вызовов → рост стоимости и времени.

**Цель:** Контролировать использование ANALYST и ARCH без блокировки необходимых вызовов.

---

#### ANALYST Limits

| Правило | Значение |
|---------|----------|
| **Базовый лимит** | 1 вызов на задачу |
| **Повторный вызов** | Только с `[OVERRIDE: force ANALYST]` |
| **Trigger** | По auto-rules (UX, A/B, ambiguity) |

**Разрешён свободно если:**
- ✅ task_type == UX
- ✅ Есть A/B выбор
- ✅ Есть продуктовая неопределённость

---

#### ARCH Limits

| Правило | Значение |
|---------|----------|
| **Базовый лимит** | 1 вызов на задачу |
| **Повторный вызов** | Только если: `[OVERRIDE: force ARCH]` или TEST вернул FAIL с architectural concern |
| **Trigger** | По auto-rules (scope >100 LOC, multi-component, state/concurrency) |

**Второй вызов разрешён если:**
- ✅ `[OVERRIDE: force ARCH]` от PM
- ✅ TEST вернул FAIL с комментарием "architectural concern"
- ✅ DEV явно пометил `risk: architectural` в PLAN

---

#### Downgrade Rule (ARCH запрет)

**ARCH запрещён (даже если PM сомневается) если:**

| Условие | Почему |
|---------|--------|
| Локальная задача (single-file) | Нет архитектурных последствий |
| `changed_files == 1` | Один компонент |
| `estimated_scope < 100 LOC` | Небольшое изменение |

**В этом случае:**
- ❌ ARCH не вызывается
- ✅ Используется только DEV + TEST
- ✅ PM может запросить ARCH только с `[OVERRIDE: force ARCH]` + явное обоснование

---

#### Cost Logging

**Каждый OWNER_SUMMARY должен включать:**

```markdown
### ROLE_COST
- analyst_calls: N
- arch_calls: N
- cost_control_triggered: yes/no
```

**Пример:**
```markdown
### ROLE_COST
- analyst_calls: 1
- arch_calls: 0
- cost_control_triggered: no
```

**cost_control_triggered = yes если:**
- ARCH был заблокирован по downgrade rule
- Повторный вызов ANALYST/ARCH был отклонён без override
- PM attempted to call ARCH для single-file задачи

---

#### Cost Control Decision Table

| Ситуация | ANALYST | ARCH |
|----------|---------|------|
| UX выбор (A/B) | ✅ 1 вызов | ❌ no |
| Bug fix <50 LOC | ❌ no | ❌ no (downgrade) |
| Refactor 150 LOC, 3 файла | ❌ no | ✅ 1 вызов |
| State machine change | ❌ no | ✅ 1 вызов |
| Single-file, PM сомневается | ❌ no | ❌ no (downgrade, нужен override) |

---

#### Override Examples

```
[OVERRIDE: force ARCH — интеграция с внешним API, высокий риск]
[OVERRIDE: force ANALYST — UX не зафиксирован, нужно мнение]
[OVERRIDE: skip ARCH — простой фикс, несмотря на scope]
```

---

#### Decision Flow Diagram

```
1. PM: Receive task (task_description, task_type, estimated_scope)
   ↓
2. ANALYST CHECK: task_type==UX? OR contains "вариант/layout/UX/выбор/A/B"? OR ambiguity?
   → YES: use_analyst = true
   → NO: use_analyst = false
   ↓
3. DEV: Implement (always)
   ↓
4. ARCH CHECK: estimated_scope>100 LOC? OR changed_files>1? OR contains "refactor/архитектура/state"? OR integration risk?
   → YES: use_arch = true
   → NO: use_arch = false
   ↓
5. TEST: Verify (always)
   ↓
6. OWNER_SUMMARY + ROLE_DECISION log
```

---

### 2.3 PM_EXECUTION_GATE

**Проблема:** Агент может перескакивать в свободный analysis-style ответ без PM-координации.

**Решение:** PM — единственная точка входа и выхода для task execution.

---

#### PM ОБЯЗАННОСТИ

**PM обязан:**
1. Классифицировать задачу (bug / feature / UX / refactor / docs)
2. Выбрать режим выполнения (DIRECT_MAIN / SAFE_BRANCH)
3. Определить, нужен ли ANALYST/DEV/TEST/ARCH
4. Собрать OWNER_SUMMARY в конце

**Запрещено:**
- ❌ Перескакивать сразу в свободный analysis-style ответ
- ❌ Начинать реализацию без PM-классификации
- ❌ Пропускать PM-координацию для execution tasks

---

#### EXECUTION_VS_ANALYSIS

| Тип запроса | Режим |
|-------------|-------|
| "Нашёл багу: ..." | EXECUTION (PM → DEV → TEST) |
| "Сделай X" | EXECUTION (PM → DEV → TEST) |
| "Как лучше сделать X?" | ANALYSIS (PM → ANALYST optional) |
| "Что думаешь про X?" | FREE (без pipeline) |

**Для EXECUTION задач:**
→ PM обязан довести до результата (fix / commit / push / deploy status)

---

### 2.4 Enforcement Rules (критично)

- ❌ **НЕЛЬЗЯ** выполнять изменения кода напрямую в main session
- ❌ **НЕЛЬЗЯ** пропускать TEST этап
- ❌ **НЕЛЬЗЯ** коммитить без TEST PASS
- ✅ **Любой код** → только через DEV subagent (`sessions_spawn` с `model: "qwen3-coder-plus"`)
- ✅ **Любая проверка** → только через TEST subagent (`sessions_spawn` с `model: "qwen3-coder-plus"`)
- ✅ **ARCH** → только при state machine / routing bug / risky architecture

### 2.4 Pipeline Flow

**Базовый pipeline:**
```
PM → (ANALYST?) → DEV → (ARCH?) → TEST → OWNER_SUMMARY
```

**Полный flow:**
```
1. PM (qwen3.5-plus)
   ↓
   sessions_spawn(task="...", model="qwen3.5-plus")
   
2. ANALYST (qwen3.5-plus) [ЕСЛИ ЕСТЬ UX НЕОПРЕДЕЛЁННОСТЬ]
   ↓
   sessions_spawn(task="Analyze UX options...", model="qwen3.5-plus")
   
3. DEV (qwen3-coder-plus)
   ↓
   sessions_spawn(task=pm.output, model="qwen3-coder-plus")
   
4. ARCH (qwen3-max-2026-01-23) [ЕСЛИ ЕСТЬ ARCH RISK]
   ↓
   sessions_spawn(task="Assess architectural risks...", model="qwen3-max-2026-01-23")
   
5. TEST (qwen3-coder-plus)
   ↓
   sessions_spawn(task="Проверь изменения...", model="qwen3-coder-plus")
   
6. OWNER_SUMMARY
```

**Примеры:**

| Задача | Pipeline |
|--------|----------|
| UX выбор (AG-007) | PM → ANALYST → DEV → TEST |
| Простой bug fix | PM → DEV → TEST |
| Сложный refactor | PM → DEV → ARCH → TEST |

### 2.5 Config Requirements

```json5
{
  agents: {
    list: [{
      id: "agonarena",
      subagents: {
        allowModelOverride: true,  // ОБЯЗАТЕЛЬНО
        allowedModels: [
          "modelstudio/qwen3.5-plus",
          "modelstudio/qwen3-coder-plus",
          "modelstudio/qwen3-max-2026-01-23"
        ]
      }
    }]
  }
}
```

---

### 2.6 ORCHESTRATION_FLOW

**Проблема:** Оркестрация размазана по многим sections — нет единого end-to-end flow описания.

**Решение:** Явный end-to-end pipeline с handoff контрактами.

---

#### End-to-End Pipeline

```
PM → [ANALYST?] → DEV → [ARCH?] → TEST → PM → OWNER_SUMMARY
```

**Cross-references:**
- Role Triggers: Section 2.2.1
- AUTO_ROLE_SELECTION: Section 2.2.2
- PIPELINE_HANDOFF_RULES: Section 5.7
- SUBAGENT_WORKFLOW.md: полные примеры pipeline
- PIPELINE_ORCHESTRATION.md: реализация auto-spawn

---

#### Handoff Contracts

| Handoff | Инициатор | Что передаётся | Expected Output |
|---------|-----------|----------------|-----------------|
| **PM → ANALYST** | PM | task_description, UX_uncertainty, options_to_compare | ANALYST recommendation (A/B choice, UX decision) |
| **PM → DEV** | PM | task_description, acceptance_criteria, context_files, ANALYST_output (если был) | DEV PLAN + READY_FOR_TEST: yes |
| **DEV → TEST** | DEV (маркер) | READY_FOR_TEST: yes маркер + changed_files | TEST PASS/FAIL + policy_compliance check |
| **TEST → PM** | TEST | PASS/FAIL статус, violations (если есть) | PM собирает OWNER_SUMMARY |
| **PM → OWNER_SUMMARY** | PM | PM + DEV + TEST + ARCH результаты | Финальное сообщение пользователю |

---

#### PM → DEV Handoff

**Контракт:**
- PM передаёт: `task_description`, `acceptance_criteria`, `context_files`
- Если был ANALYST: добавить `ANALYST_output`
- Механизм: `sessions_spawn(task="<PM output>", model="qwen3-coder-plus")`

**Пример:**
```
PM → DEV:
"Задача: AG-019 — исправить таймер раунда
Acceptance: таймер не отправляет сообщение после ручного завершения
Контекст: app/services/round_timer_service.py"
```

---

#### DEV → TEST Handoff

**Контракт:**
- DEV завершает ответ маркером: `READY_FOR_TEST: yes`
- TEST спавнится автоматически (Section 5.7)
- Fallback: 5 секунд → force spawn

**Пример:**
```
DEV Output:
CHANGES:
- round_timer_service.py: added status check

READY_FOR_TEST: yes
```

---

#### TEST → PM Return

**Контракт:**
- TEST возвращает: `PASS/FAIL` + `violations` (если есть)
- PM читает результат из session history
- PM агрегирует в OWNER_SUMMARY

**Пример:**
```
TEST Output:
TEST_REPORT:
- CODE_CHECK: ok
- POLICY_CHECK: ok

TEST_DECISION: PASS
```

---

#### OWNER_SUMMARY Assembly

**Кто собирает:** PM

**Формат:** Section 3.5

**Доставка:** Section 3.4 Delivery Matrix

**Пример:**
```markdown
TASK_ID: AG-019
STATUS: DONE
SUMMARY: Исправлен таймер раунда
DEV: round_timer_service.py (+8 lines)
TEST: PASS
DEPLOY: DEPLOYED
```

---

### 2.7 SUBAGENT_RESULT_RETURN

**Проблема:** Нет явного правила как результаты субагентов возвращаются в PM.

**Решение:** Все субагенты возвращают результаты в PM для агрегации.

---

#### Правило

**Все субагенты (ANALYST, DEV, ARCH, TEST):**
- ✅ Возвращают результаты в parent session (где работает PM)
- ✅ Используют `sessions_spawn` с `mode="run"` (результат в parent)
- ✅ Не доставляют итог напрямую пользователю

**PM:**
- ✅ Читает результаты из session history
- ✅ Агрегирует в OWNER_SUMMARY формат
- ✅ Доставляет OWNER_SUMMARY пользователю

---

#### Запрещено

| Паттерн | Почему |
|---------|--------|
| ❌ Субагенты напрямую в Telegram | PM = single exit point |
| ❌ Пропускать PM при агрегации | Нет единого формата |
| ❌ Несколько OWNER_SUMMARY | Дублирование, шум |

---

#### Механизм

```
1. PM spawns ANALYST/DEV/ARCH/TEST via sessions_spawn
   ↓
2. Subagent выполняет задачу
   ↓
3. Subagent результат → parent session (автоматически)
   ↓
4. PM читает результат из session history
   ↓
5. PM агрегирует все результаты в OWNER_SUMMARY
   ↓
6. PM доставляет OWNER_SUMMARY пользователю
```

---

## 3. INTERACTIVE DELIVERY RULE

### 3.1 Проблема

Результаты PM/DEV/TEST subagent по умолчанию остаются в сессии и **не попадают в Telegram**. Вопросы PM к пользователю теряются.

### 3.2 Правило доставки

**PM_OUTPUT классификация:**

| Тип | Детекция | Доставка |
|-----|----------|----------|
| **QUESTION** | Содержит `?`, `выбери`, `уточни`, `подтверди`, `нужно решение` | **Немедленно в Telegram** |
| **PLAN** | План реализации, список файлов | Агрегировать в OWNER_SUMMARY |
| **INFO** | Информация, контекст, анализ | Агрегировать в OWNER_SUMMARY |

### 3.3 Реализация для QUESTION

**Правило:** Доставлять в **ту же сессию**, из которой пришёл исходный запрос (parent session).

```typescript
// После получения PM результата:
if (pmOutput.match(/[?]|выбери|уточни|подтверди|нужно решение/i)) {
  // Это вопрос — отправить в родительскую сессию (откуда пришёл запрос)
  // sessions_send без явного sessionKey доставляет в текущую сессию
  sessions_send({
    message: `📋 PM QUESTION:\n${pmOutput}`
    // sessionKey не указан → доставляется в parent session автоматически
  });
  
  // Ждать ответа пользователя перед продолжением pipeline
}
```

**Альтернатива (явный parent target):**
```typescript
// Если требуется явная доставка в parent session:
sessions_send({
  target: "parent",  // или использовать currentSessionKey из runtime context
  message: `📋 PM QUESTION:\n${pmOutput}`
});
```

**Важно:** Никогда не использовать hardcoded sessionKey/chat_id. Всегда доставлять back to originating session.

---

### 3.3.1 PM Question Rate Control (Anti-Noise)

**Проблема:** PM может генерировать много вопросов подряд → Telegram зашумляется.

**Правило:**

| Limit | Value |
|-------|-------|
| **Максимум вопросов за шаг pipeline** | 1 |
| **Максимум вопросов на задачу** | 3 |
| **При превышении** | Агрегировать в batch |

**Batching Rule:**

Вместо:
```
❌ Вопрос 1: ...
❌ Вопрос 2: ...
❌ Вопрос 3: ...
```

Сделать:
```
✅ 1 сообщение:

"📋 Нужно уточнить:
1. ...
2. ...
3. ..."
```

**Fallback:**
- Если PM генерирует >3 вопросов → **автоматически агрегировать** в одно сообщение
- Формат: нумерованный список всех вопросов
- Пользователь отвечает на все вопросы в одном ответе

**Implementation:**
```typescript
// Счётчик вопросов в рамках задачи
let questionCount = 0;
const MAX_QUESTIONS_PER_TASK = 3;

if (pmOutput.match(/[?]|выбери|уточни|подтверди/i)) {
  questionCount++;
  
  if (questionCount > MAX_QUESTIONS_PER_TASK) {
    // Агрегировать в batch вместо отправки
    batchQuestions.push(pmOutput);
  } else {
    // Отправить вопрос
    sessions_send({ message: `📋 PM QUESTION:\n${pmOutput}` });
  }
}
```

---

### 3.3.2 Decision Without Question (Anti-Unnecessary-Ask)

**Проблема:** PM может задавать вопросы, ответы на которые уже зафиксированы в policy или предыдущих решениях.

**Правило:** PM НЕ должен задавать вопрос пользователю, если решение можно принять из:

| Источник | Пример |
|----------|--------|
| **AGENT_POLICY.md** | Зафиксированные правила разработки |
| **SUBAGENT_WORKFLOW.md** | Pipeline и workflow правила |
| **state/TODO.md** | Приоритеты задач (P0/P1/P2/P3) |
| **state/PROJECT_STATE.md** | Текущее состояние проекта |
| **product/ACCEPTANCE.md** | Протоколы приёмки |
| **state/DEVLOG.md / PROMPTS.md** | Ранее зафиксированные user decisions |

**PM задаёт вопрос ТОЛЬКО если:**

| Условие | Описание |
|---------|----------|
| ❌ Нет policy | В документации нет ответа |
| ❌ 2+ допустимых варианта | Нет зафиксированного предпочтения |
| ✅ Влияет на UX / product / release | Решение влияет на продукт |

**Precedence Rule:**

```
1. Сначала искать existing decision
   → state/DEVLOG.md, PROMPTS.md, state/PROJECT_STATE.md
   
2. Потом искать policy
   → AGENT_POLICY.md, state/TODO.md, product/ACCEPTANCE.md
   
3. Только потом спрашивать пользователя
   → Если нет policy и нет previous decision
```

**Implementation Pattern:**
```typescript
// Перед генерацией вопроса:
const existingDecision = searchInFiles([
  'state/DEVLOG.md',
  'PROMPTS.md', 
  'state/PROJECT_STATE.md',
  'AGENT_POLICY.md',
  'state/TODO.md'
], questionTopic);

if (existingDecision) {
  // Использовать existing decision, НЕ спрашивать
  applyDecision(existingDecision);
} else if (hasPolicyFor(questionTopic)) {
  // Использовать policy, НЕ спрашивать
  applyPolicy(questionTopic);
} else {
  // Нет policy и нет previous decision → спросить
  sessions_send({ message: `📋 PM QUESTION:\n${question}` });
}
```

**Examples:**

| Ситуация | Ask? | Почему |
|----------|------|--------|
| Какой моделью делать код? | ❌ Нет | Policy: qwen3-coder-plus |
| Какой вариант layout для AG-007? | ✅ Да | User preference, нет policy |
| Нужно ли тестировать перед коммитом? | ❌ Нет | Policy: TEST обязателен |
| Какой приоритет у задачи? | ❌ Нет | state/TODO.md: P0/P1/P2/P3 |
| Какой формат scenario picker? | ✅ Да | UX choice, пользователь решает |

---

### 3.4 Delivery Matrix

| Роль | Тип вывода | Доставка |
|------|------------|----------|
| **PM** | QUESTION | ✅ Немедленно в Telegram |
| **PM** | PLAN/INFO | ⏳ В OWNER_SUMMARY |
| **DEV** | Любой | ⏳ В OWNER_SUMMARY |
| **TEST** | Любой | ⏳ В OWNER_SUMMARY |
| **ARCH** | Любой | ⏳ В OWNER_SUMMARY |
| **OWNER_SUMMARY** | Финальный | ✅ В Telegram |

### 3.5 OWNER_SUMMARY Format

```markdown
TASK_ID: AG-XXX

STATUS: DONE | REWORK | BLOCKED

SUMMARY:
<краткое описание выполненного>

PM:
<резюме от PM>

DEV:
<изменения, файлы>

TEST:
<результаты тестов, PASS/FAIL>

NEXT_ACTIONS:
- <следующий шаг 1>
- <следующий шаг 2>
```

---

### 3.6 AUTO_NEXT_TASK

**Проблема:** После завершения задачи пользователь должен вручную выбирать следующую → трата времени на контекст.

**Решение:** PM автоматически предлагает следующую задачу на основе state/TODO.md и state/PROJECT_STATE.md.

---

#### Правило

**После каждого OWNER_SUMMARY PM обязан:**

1. Прочитать `state/TODO.md` и `state/PROJECT_STATE.md`
2. Найти следующую задачу:
   - **P0** → если есть (highest priority)
   - **Иначе P1 с максимальным RICE score**
3. Сформировать предложение следующей задачи

---

#### Формат Предложения

```markdown
📌 NEXT TASK SUGGESTION

**Task:** AG-XXX
**Title:** ...
**Priority:** P0/P1/P2/P3
**RICE Score:** N (если применимо)

**Почему:**
- <обоснование выбора>

**Scope:**
- <краткое описание задачи>

❓ Запустить эту задачу? (yes/no)
```

---

#### Delivery Rule

- ✅ Это сообщение **ВСЕГДА** отправляется в Telegram
- ✅ Это **НЕ OWNER_SUMMARY**, а отдельное сообщение от PM
- ✅ Использовать тот же target rule (parent session)

**Implementation:**
```typescript
// После OWNER_SUMMARY:
sessions_send({
  message: `📌 NEXT TASK SUGGESTION

**Task:** AG-XXX
**Title:** ...
...

❓ Запустить эту задачу? (yes/no)`
});
```

---

#### User Response Handling

| Response | Action |
|----------|--------|
| **"yes"** | Запустить pipeline для предложенной задачи |
| **"no"** | PM предлагает следующую альтернативу из backlog |
| **Молчание** | Ничего не запускать, ждать явной команды |

---

#### Task Selection Algorithm

```
1. Есть ли P0 задачи в state/TODO.md?
   - YES → Выбрать P0 с highest RICE
   - NO → перейти к шагу 2

2. Есть ли P1 задачи в state/TODO.md?
   - YES → Выбрать P1 с highest RICE
   - NO → перейти к шагу 3

3. Есть ли P2/P3 задачи?
   - YES → Предложить top P2
   - NO → "Backlog пуст, ждём новых задач"
```

---

#### Anti-Automation Rule

**Важно:**
- ❌ **НЕ запускать** задачи автоматически без подтверждения
- ✅ **Только предложение** + ожидание ответа пользователя

**Pipeline стартует ТОЛЬКО после:**
- Явного "yes" от пользователя
- Или явной команды вида "запусти AG-XXX"

---

#### Example

```markdown
📌 NEXT TASK SUGGESTION

**Task:** AG-006
**Title:** Commit and push validated release after manual PASS
**Priority:** P0
**RICE Score:** 288

**Почему:**
- AG-005 и AG-007 закрыты с Telegram acceptance PASS
- AG-011 (voice fix) готов с тестами 6/6 PASS
- Release policy требует commit+push после acceptance
-Highest RICE в backlog

**Scope:**
- Commit: AG-005, AG-007, AG-011 changes
- Push: origin/feature/menu-ux-refresh
- Evidence: branch/hash в state/DEVLOG.md

❓ Запустить эту задачу? (yes/no)
```

---

## 4. Safety rules

- Использовать только `final message.content`
- Reasoning output не включать в Telegram/TUI/summaries/context
- Retries = 1
- Без параллельных subagent вызовов
- При model error: остановить pipeline → OWNER_SUMMARY с BLOCKER

---

## 5. Delivery

- **Telegram = primary**
- **TUI = debug only**
- **Формат:** OWNER_SUMMARY (STATUS/CURRENT/BLOCKER/NEXT/NEED_DECISION)
- **Вопросы PM:** немедленно в Telegram через `sessions_send`
- **Target rule:** Всегда доставлять в **parent session** (откуда пришёл запрос)

**DELIVERY_RULE (обязательно):**
```
✅ sessions_send({ sessionKey: currentParentSessionKey, message: "..." })
```

**Где брать sessionKey:**
- Из runtime context (inbound metadata)
- Формат: `agent:agonarena:telegram:group:-4998914548`
- Динамически, НЕ hardcoded

**Запрещено:**
- ❌ `sessions_send({ message })` без sessionKey
- ❌ hardcoded `sessionKey: "telegram:..."`

- **OWNER_SUMMARY:** Тот же target rule — explicit dynamic sessionKey

---

## 5.1 DELIVERY_SINGLE_SOURCE_OF_TRUTH

**Проблема:** Два механизма (message + sessions_send) создают inconsistent routing.

**Решение:** Единый инструмент для каждого типа доставки.

### DELIVERY_MATRIX

| Тип | Инструмент | Когда |
|-----|------------|-------|
| **USER-FACING (Telegram)** | `message` tool | Всегда для Telegram |
| **INTERNAL (session-to-session)** | `sessions_send` | Только internal coordination |

### USER-FACING (Telegram)

**✅ ИСПОЛЬЗОВАТЬ:**
```
message({
  action: "send",
  target: "<chat_id>",
  channel: "telegram",
  message: "..."
})
```

**Применение:** PM QUESTION, OWNER_SUMMARY, NEXT TASK, READY_FOR_*, любые сообщения пользователю

### INTERNAL (Session-to-Session)

**✅ ИСПОЛЬЗОВАТЬ:**
```
sessions_send({
  sessionKey: "agent:agonarena:subagent:xxx",
  message: "..."
})
```

**Применение:** PM→DEV handoff, DEV→TEST handoff, subagent coordination

### ЗАПРЕЩЕНО

| Паттерн | Почему |
|---------|--------|
| ❌ `sessions_send` для Telegram | Session lock, не надёжно |
| ❌ `message` для internal | Нет session tracking |
| ❌ Смешивать механизмы | Inconsistent routing |

---

## 5.6 TASK_ID_SOURCE_OF_TRUTH

**Проблема:** PM генерирует task_id (AG-XXX) без доступа к state/TODO.md → риск галлюцинаций.

**Решение:** Запретить генерацию новых ID. Использовать только существующие из файлов.

---

### ИСТОЧНИК ИСТИНЫ

| Источник | Приоритет |
|----------|-----------|
| **state/TODO.md** | Основной (список задач) |
| **state/PROJECT_STATE.md** | Дополнительный (контекст) |

---

### ПРАВИЛО

**❌ ЗАПРЕЩЕНО:**
- Придумывать AG-XXX
- Генерировать новые ID в NEXT TASK SUGGESTION

**✅ ОБЯЗАТЕЛЬНО:**
1. Прочитать state/TODO.md перед NEXT TASK SUGGESTION
2. Найти следующую задачу в backlog
3. Использовать реальный ID из файла

**Если ID НЕ найден:**
- Не показывать ID вообще
- Использовать формат без ID (см. ниже)

---

### ФОРМАТ: NEXT TASK (с ID)

```
📌 Следующая задача: AG-XXX

Название: ...
Приоритет: ...
Почему: ...
Scope: ...

❓ Запустить? (yes/no)
```

---

### ФОРМАТ: NEXT TASK (без ID)

```
📌 Следующая задача

Название: ...
Приоритет: ...
Почему: ...
Scope: ...

❓ Запустить? (yes/no)
```

---

## 5.7 PIPELINE_HANDOFF_RULES

**Проблема:** Pipeline застревает после DEV → TEST handoff, TEST не запускается автоматически.

**Решение:** Обязательный маркер DEV completion + авто-спавн TEST.

---

### DEV COMPLETION CONTRACT

**DEV обязан завершить ответ маркером:**
```
READY_FOR_TEST: yes
```

**Без маркера:**
- HANDOFF считается неполным
- TEST не будет запущен

---

### ORCHESTRATION RULE

**Если получено:**
```
READY_FOR_TEST: yes
```

**→ Автоматически выполнить:**
```
sessions_spawn({
  role: "TEST",
  model: "qwen3-coder-plus",
  task: "TEST current task"
})
```

**Implementation:**
- Auto-spawn mechanism implemented in `scripts/auto_test_spawner.py`
- Monitors session files for READY_FOR_TEST marker
- Includes 5-second fallback timer to ensure TEST spawn
- See `PIPELINE_ORCHESTRATION.md` for full implementation details

---

### ЗАПРЕЩЕНО

| Паттерн | Почему |
|---------|--------|
| ❌ Ожидание ручного триггера TEST | Pipeline застревает |
| ❌ Завершение без TEST | Нет валидации |
| ❌ DEV без READY_FOR_TEST маркера | Оркестрация не сработает |

---

### FALLBACK (5 секунд)

**Если TEST не запущен в течение 5 сек после DEV:**
→ Принудительно заспавнить TEST

**Реализация:**
- Таймер после DEV completion
- Если TEST не spawned → force spawn
- Логировать fallback activation

---

## 6. Logging

| Файл | Назначение |
|------|------------|
| `state/DEVLOG.md` | История решений и изменений |
| `PROMPTS.md` | Архив промтов и результатов |
| `state/TODO.md` | Backlog и статусы задач |
| `state/PROJECT_STATE.md` | Текущее состояние проекта |
| `product/ACCEPTANCE.md` | Протоколы ручной приёмки |

### Правила логирования

- ✅ Каждая задача логируется в state/DEVLOG.md
- ✅ Каждая роль пишет свой этап
- ✅ Промты сохраняются в PROMPTS.md
- ✅ Сохраняется история решений
- ✅ Статусы обновляются в state/TODO.md

---

## 7. GIT_WORKFLOW_RULES

**Проблема:** Push в промежуточном состоянии ломает CI/CD и создаёт нестабильные релизы.

**Решение:** Commit после каждого логического изменения, push только на стабильном checkpoint.

---

### COMMIT RULES

**Commit после:**
- ✅ Каждого завершённого task (AG-XXX)
- ✅ Каждого policy изменения
- ✅ Каждого bug fix с TEST PASS

**Commit message формат:**
```
<type>: <description>

- Task: AG-XXX (если применимо)
- Changes: список файлов
- Tests: PASS/FAIL
```

**Типы:**
- `feat` — новая функциональность
- `fix` — bug fix
- `docs` — documentation update
- `policy` — policy/workflow изменение
- `refactor` — рефакторинг без изменений поведения

---

### PUSH CHECKPOINTS

**Push разрешён ТОЛЬКО если:**

| Check | Требуется |
|-------|-----------|
| **TEST PASS** | ✅ Все тесты зелёные |
| **Delivery работает** | ✅ Telegram delivery OK |
| **Pipeline не в промежуточном состоянии** | ✅ Нет зависших handoff |
| **TASK завершена** | ✅ AG-XXX → DONE |

**Push запрещён:**
- ❌ При незавершённой задаче
- ❌ При сломанном pipeline (DEV→TEST stall)
- ❌ При TEST FAIL
- ❌ При delivery issues

---

### STABLE STATE DEFINITION

**Стабильное состояние:**
```
[CHECKPOINT]
- ✅ TEST PASS
- ✅ Delivery: OK
- ✅ Pipeline: no stalled handoffs
- ✅ Task: AG-XXX → DONE
- ✅ state/DEVLOG.md: обновлён
- ✅ state/TODO.md: статус обновлён
     ↓
PUSH TO ORIGIN
```

---

### WORKFLOW EXAMPLE

```
1. Task AG-XXX initiated
   ↓
2. PM → DEV → TEST pipeline
   ↓
3. TEST PASS received
   ↓
4. Update state/TODO.md (AG-XXX → DONE)
   ↓
5. Update state/DEVLOG.md (entry added)
   ↓
6. git add <files>
   ↓
7. git commit -m "type: description"
   ↓
8. [CHECKPOINT] Verify stable state
   ↓
9. git push origin <branch>
```

---

### EMERGENCY REVERT

**Если push сломал production:**
```
1. git revert HEAD
2. git push origin <branch>
3. state/DEVLOG.md: добавить entry о revert
4. Исправить в новой задаче AG-XXX
```

---

## 8. EXECUTION_COMPLETION_RULE

**Проблема:** Агент останавливается на анализе / safe fix proposal без доведения до фактического результата.

**Решение:** Для execution-задач обязательный полный цикл до deploy status.

---

#### DEFAULT EXPECTATION

**Если пользователь запросил исправление бага / внесение изменения:**

```
1. analyze (причина, scope)
2. implement (фактическое изменение)
3. validate (TEST PASS)
4. show changed files + diff summary
5. update required project docs/state (только если justified by policy)
6. commit
7. push (в DIRECT_MAIN mode), если пользователь не запретил явно
8. сообщить deploy status
```

**Агент НЕ должен останавливаться на:**
- ❌ Только анализе причины
- ❌ Только safe fix proposal
- ❌ Списке идей без реализации

---

#### DEPLOY_STATUS_RULE

**После bugfix/task execution агент обязан явно указать один из статусов:**

---

##### DEPLOYMENT DEFINITION (agonarena_bot)

**Для проекта agonarena_bot:**
- ❌ **commit/push/merge ≠ deploy**
- ✅ **deploy = running Docker container updated**

**Изменение считается задеплоенным только когда:**
- Код в git (committed + pushed) **И**
- Docker-контейнер пересобран и перезапущен с новой версией **И**
- Бот в Telegram отвечает с новым поведением

---

##### STATUS DEFINITIONS

| Статус | Когда |
|--------|-------|
| **DEPLOYED** | Изменение применено в работающем Docker-контейнере. Бот использует новую версию. |
| **NOT_DEPLOYED** | Код изменён / commit сделан / push сделан, но Docker-контейнер ещё не обновлён. |
| **DEPLOY_PENDING** | Код готов, известен точный следующий шаг до обновлённого Docker-контейнера. |

---

##### EXAMPLES

**DEPLOYED:**
```
📦 DEPLOY STATUS: DEPLOYED

Docker-контейнер обновлён, бот использует новую версию.
```

**NOT_DEPLOYED:**
```
📦 DEPLOY STATUS: NOT_DEPLOYED

Код закоммичен и запушен, но Docker-контейнер требует ручного обновления.
Следующий шаг:
```bash
docker-compose pull && docker-compose up -d --force-recreate
```
```

**DEPLOY_PENDING:**
```
📦 DEPLOY STATUS: DEPLOY_PENDING

Следующий шаг:
```bash
docker-compose build && docker-compose up -d
```
```

---

##### ЗАПРЕЩЕНО

| Паттерн | Почему |
|---------|--------|
| ❌ Ставить DEPLOYED после commit/push | Контейнер может быть не обновлён |
| ❌ Ставить DEPLOYED после merge в main | Контейнер требует отдельного update |
| ❌ Не указывать следующий шаг при DEPLOY_PENDING | Пользователь не знает как завершить deploy |
| ❌ Оставлять impression, что задача завершена без Docker update | Изменение не работает в production |

---

##### DEPLOY COMMANDS (reference)

**Обновление Docker-контейнера:**
```bash
# Pull + rebuild + restart
docker-compose pull
docker-compose build
docker-compose up -d --force-recreate

# Или одной командой
docker-compose pull && docker-compose build && docker-compose up -d --force-recreate
```

**Проверка:**
```bash
docker-compose ps
docker-compose logs -f bot
```

---

##### ЗАПРЕЩЕНО

- ❌ Оставлять impression, что задача завершена, если код не доставлен
- ❌ Не указывать следующий шаг при DEPLOY_PENDING

---

## 9. MEMORY_WRITE_RULE

**Проблема:** Агент обновляет memory/* без явной необходимости.

**Решение:** memory/* не обновлять по умолчанию в обычных execution tasks.

---

#### ПРАВИЛО

**memory/* можно трогать только если:**
- ✅ Пользователь явно просит
- ✅ Есть специальный режим / отдельная задача на memory continuity
- ✅ Это end-of-day session wrap-up

**Для bugfix/doc/policy/refactor задач:**
- ❌ memory/* **НЕ** является обязательным update target
- ✅ Обновлять только state/DEVLOG.md, state/TODO.md, state/PROJECT_STATE.md при необходимости

---

#### DEFAULT BEHAVIOR

| Тип задачи | memory/* update? |
|------------|------------------|
| Bug fix | ❌ No |
| Policy update | ❌ No |
| Refactor | ❌ No |
| Feature implementation | ❌ No |
| Memory continuity task | ✅ Yes |
| User explicitly requests | ✅ Yes |

---

## 10. PROJECT_DOC_UPDATE_SCOPE

**Проблема:** Агент автоматически меняет PROJECT_CONTEXT_SUMMARY.md без достаточного обоснования.

**Решение:** Чёткие критерии для обновления project docs.

---

#### PROJECT_CONTEXT_SUMMARY.md

**Обновлять только если:**
- ✅ Реально изменился bootstrap/navigation/project-wide state
- ✅ Это отдельная docs task
- ✅ Изменение явно нужно по смыслу (major milestone)

**Для обычного bugfix чаще релевантны:**
- state/DEVLOG.md
- state/PROJECT_STATE.md
- state/TODO.md

**И только если изменение действительно отражает состояние проекта.**

---

#### DEFAULT BEHAVIOR

| Тип задачи | PROJECT_CONTEXT_SUMMARY.md | state/*.md |
|------------|---------------------------|------------|
| Bug fix | ❌ No | ✅ If relevant |
| Policy update | ❌ No | ✅ DEVLOG.md |
| Major milestone | ✅ Yes | ✅ Yes |
| Docs task | ✅ If scope | ✅ Yes |

---

## 11. POST_TASK_SANITY_CHECK

**Проблема:** После изменений появляются stray root duplicates и мусор.

**Решение:** Обязательная проверка workspace после любых изменений.

---

#### CHECKLIST

**После любых изменений агент обязан проверить:**

```bash
git status --short
```

**Проверить:**
- ✅ Не появились ли stray root duplicates для canonical crew files
- ✅ Не были ли случайно созданы forbidden root copies:
  - AGENTS.md
  - HEARTBEAT.md
  - IDENTITY.md
  - SOUL.md
  - TOOLS.md
  - USER.md
- ✅ Не появился ли неожиданный мусор вне scope задачи

---

#### STRAY DUPLICATES HANDLING

**Если stray duplicates появились:**
- ❌ **НЕ коммитить** их
- ✅ Пометить как cleanup candidates
- ✅ Предложить удалить (trash/rm)
- ✅ Canonical files редактировать только в crew/

---

#### CANONICAL CREW PATHS

| Файл | Canonical path |
|------|----------------|
| AGENTS.md | `crew/AGENTS.md` |
| HEARTBEAT.md | `crew/HEARTBEAT.md` |
| IDENTITY.md | `crew/IDENTITY.md` |
| SOUL.md | `crew/SOUL.md` |
| TOOLS.md | `crew/TOOLS.md` |
| USER.md | `crew/USER.md` |

**Запрещено:**
- ❌ Создавать эти файлы в repository root
- ❌ Редактировать root-копии вместо canonical files

---

## 12. TOKEN_OBSERVABILITY

**Проблема:** Нет видимости расхода токенов на pipeline этапы.

**Решение:** Lightweight token tracking без новой роли.

---

### RULES

1. **НЕ создавать новую роль** — использовать существующие
2. **Использовать TEST или OWNER_SUMMARY** — добавить token блок
3. **НЕ делать сложные вычисления** — только approximate
4. **НЕ вызывать дополнительные модели** — только наблюдение

---

### TOKEN_USAGE BLOCK

**Каждый OWNER_SUMMARY должен включать:**

```markdown
### TOKEN_USAGE
- approx_prompt_tokens: N
- approx_completion_tokens: N
- largest_step: PM/DEV/TEST/ARCH
- optimization_hint: <1 строка>
```

**Пример:**
```markdown
### TOKEN_USAGE
- approx_prompt_tokens: 15000
- approx_completion_tokens: 3500
- largest_step: DEV
- optimization_hint: DEV context можно сжать на 20%
```

---

### ESTIMATION (Lightweight)

**Метод:**
- Prompt tokens: сумма input токенов всех stages
- Completion tokens: сумма output токенов всех stages
- Largest step: stage с максимальным input+output
- Optimization hint: 1 строка от TEST или PM

**Источники:**
- Model provider API (если доступно)
- Или approximate по размеру context

---

### OPTIMIZATION_HINT EXAMPLES

| Ситуация | Hint |
|----------|------|
| DEV context большой | "DEV context можно сжать на N%" |
| PM задаёт много вопросов | "PM questions можно сократить" |
| TEST дублирует контекст | "TEST может использовать дельту" |
| ARCH не вызывался | "ARCH не требовался — ok" |

---

### INTEGRATION

**Где добавлять:**
- В конец OWNER_SUMMARY
- После ROLE_COST и ROLE_DECISION

**Кто заполняет:**
- TEST subagent (после завершения проверок)
- Или PM (при финальном OWNER_SUMMARY)

---

## 9. VERBOSITY_CONTROL

**Проблема:** Pipeline генерирует избыточные сообщения → рост токенов и шум.

**Решение:** Строгие лимиты на длину ответов для каждой роли.

---

### VERBOSITY_POLICY

**Принцип:** Краткость > полнота

**Правило:** Если сомнение → выбирать более короткий вариант

---

### ROLE LIMITS

| Роль | Лимит | Содержание |
|------|-------|------------|
| **PM** | ≤ 5 строк | Только суть (если не вопрос) |
| **DEV** | ≤ 10 строк | Только изменения + READY_FOR_TEST |
| **TEST** | ≤ 5 строк | Только результат (PASS/FAIL + 1 причина) |
| **OWNER_SUMMARY** | ≤ 10 строк | Без дублирования |

---

### ЗАПРЕЩЕНО

| Паттерн | Почему |
|---------|--------|
| ❌ Пересказ предыдущих шагов |already в контексте |
| ❌ Длинные объяснения без запроса | Трата токенов |
| ❌ Повтор контекста |already в session history |
| ❌ "Объяснения ради объяснений" | Не добавляет ценности |

---

### EXAMPLES

**PM (правильно):**
```
📌 NEXT TASK: AG-016

Почему: Pipeline bug блокирует интеграцию
Scope: Исправить DEV→TEST handoff

Запустить? (yes/no)
```

**PM (неправильно):**
```
📌 NEXT TASK SUGGESTION

После завершения AG-009 и AG-015, следующая задача 
в backlog это AG-016, которая имеет приоритет P0, 
потому что pipeline orchestration bug блокирует 
дальнейшую интеграцию и требует исправления...
```

**DEV (правильно):**
```
CHANGES:
- menu.py: feedback button added
- config.py: FEEDBACK_OWNER_USER_ID added

READY_FOR_TEST: yes
```

**TEST (правильно):**
```
TEST_REPORT:
- BUTTON_CHECK: ok
- HANDLER_CHECK: ok
- DELIVERY_CHECK: ok

TEST_DECISION: PASS
```

---

### PRIORITY

```
1. Краткость
2. Полнота (если не противоречит 1)
3. Объяснения (только по запросу)
```

---

### INTEGRATION

**Где применять:**
- Все user-facing сообщения
- Все pipeline handoff сообщения
- Все OWNER_SUMMARY компоненты

**Кто соблюдает:**
- PM, ANALYST, DEV, ARCH, TEST — все роли

---

## 10. CONTEXT_PRUNING

**Проблема:** Контекст растёт между шагами pipeline → лишние prompt_tokens.

**Решение:** Передавать только необходимый минимум контекста.

---

### CONTEXT_POLICY

**Перед каждым шагом передавать только:**
1. Текущую задачу (task description)
2. Результат предыдущего шага (1 блок)
3. Необходимые маркеры (READY_FOR_TEST и т.д.)

---

### MAX_CONTEXT_BLOCKS = 3

**Структура:**
```
[1] TASK: <текущая задача>
[2] LAST_RESULT: <результат предыдущего шага>
[3] MARKERS: <READY_FOR_TEST / etc>
```

---

### УДАЛЯТЬ

| Тип | Почему |
|-----|--------|
| ❌ Старые обсуждения | already в session history |
| ❌ Предыдущие OWNER_SUMMARY | already зафиксированы |
| ❌ Лишние пояснения | VERBOSITY_CONTROL запрещает |

---

### ПРИОРИТЕТ

```
1. Актуальность
2. Полнота (если не противоречит 1)
3. Последний шаг важнее истории
```

---

### FALLBACK (если контекст > лимита)

**Оставить только:**
```
- task (обязательно)
- last_result (обязательно)
- critical markers (READY_FOR_TEST и т.д.)
```

**Удалить:**
- Всё остальное

---

### EXAMPLE

**Правильно (≤3 блока):**
```
[1] TASK: AG-009 — feedback button implementation
[2] LAST_RESULT: DEV completed, READY_FOR_TEST: yes
[3] MARKERS: TEST required
```

**Неправильно (>3 блока):**
```
[1] Original user request from 5 steps ago
[2] PM initial analysis
[3] ANALYST recommendations
[4] DEV plan
[5] DEV implementation
[6] Previous OWNER_SUMMARY
...
```

---

### INTEGRATION

**Где применять:**
- Все pipeline handoff (PM→DEV, DEV→TEST, etc.)
- Все subagent spawn
- Все context injection

**Кто соблюдает:**
- PM, ANALYST, DEV, ARCH, TEST — все роли

---

## 11. POLICY_ENFORCEMENT

**Проблема:** Policy может дрейфовать — роли иногда нарушают правила.

**Решение:** TEST роль дополнительно проверяет compliance.

---

### TEST POLICY CHECK

**TEST обязан проверить:**

| Check | Что проверять |
|-------|---------------|
| **VERBOSITY_CONTROL** | Соблюдены ли лимиты строк |
| **FORMAT_POLICY** | Нет ли markdown tables / псевдографики |
| **CONTEXT_POLICY** | Соблюдён ли MAX_CONTEXT_BLOCKS=3 |
| **HANDOFF_RULES** | Есть ли READY_FOR_TEST (если был DEV) |

---

### VIOLATION HANDLING

**Если нарушение обнаружено:**

```
TEST_DECISION: FAIL
Reason: policy_violation
Violation type: <тип нарушения>
```

**Примеры:**
- `violation_type: verbosity_exceeded`
- `violation_type: markdown_table_found`
- `violation_type: context_blocks_exceeded`
- `violation_type: missing_READY_FOR_TEST`

---

### OWNER_SUMMARY REQUIREMENT

**Каждый OWNER_SUMMARY должен включать:**

```markdown
### POLICY_STATUS
- status: ok / violation
- violation_type: <тип если есть>
```

**Пример (ok):**
```markdown
### POLICY_STATUS
- status: ok
```

**Пример (violation):**
```markdown
### POLICY_STATUS
- status: violation
- violation_type: verbosity_exceeded
```

---

### RULES

1. **НЕ вызывать дополнительные модели** — только проверка output
2. **НЕ усложнять pipeline** — проверка в рамках TEST
3. **FAIL при любом нарушении** — policy > completion

---

### PRIORITY

```
1. Policy compliance
2. Task completion
```

---

### INTEGRATION

**Где проверять:**
- В конце TEST stage
- Перед OWNER_SUMMARY

**Кто проверяет:**
- TEST subagent

**Что делать при violation:**
1. Вернуть FAIL
2. Указать violation_type
3. Не продолжать pipeline до fix

---

## 12. LANGUAGE_POLICY

**Проблема:** Описание задач и сообщения начинают переходить на английский → ухудшается читаемость.

**Решение:** Строгое разделение языков для разных контекстов.

---

### LANGUAGE_OUTPUT_DISCIPLINE

**В execution-ответах:**
- ✅ project/process/doc parts — писать на русском
- ✅ code / file paths / identifiers / exact commands — английский допустим

**Запрещено:**
- ❌ Смешивать большие смысловые блоки на английском без причины
- ❌ Писать user-facing сообщения на английском

**Где применять:**
- Все user-facing сообщения
- Все pipeline handoff сообщения
- Все OWNER_SUMMARY
- Все project docs (crew/, state/, product/, architecture/, docs/)

---

### ОБЯЗАТЕЛЬНЫЙ РУССКИЙ

**Где использовать:**
- Названия задач (AG-XXX Title)
- Описания задач
- PM сообщения
- OWNER_SUMMARY
- NEXT TASK SUGGESTION
- DEVLOG записи
- UX тексты (кнопки, подсказки)
- Пользовательские уведомления
- **Project markdown files:**
  - PROJECT_CONTEXT_SUMMARY.md
  - PROJECT_INDEX.md
  - Все файлы в crew/
  - Все файлы в state/
  - Все файлы в product/
  - Все файлы в architecture/
  - Все файлы в docs/

---

### РАЗРЕШЁН АНГЛИЙСКИЙ

**Где использовать:**
- Код и переменные
- API endpoints
- Технические термины (no translation needed)
- Commit messages (допускается)
- Model names (qwen3.5-plus, etc.)

---

### ЗАПРЕЩЕНО

| Паттерн | Почему |
|---------|--------|
| ❌ Генерировать задачи на английском | Ухудшает читаемость |
| ❌ User-facing сообщения на английском | Пользователь не поймёт |
| ❌ Смешивать языки в одном предложении | Confusing |

---

### AUTO-CORRECTION

**Если обнаружен английский:**
→ Автоматически перевести на русский

**Пример:**
```
Было: "Fix DEV → TEST auto-handoff"
Стало: "Исправить авто-передачу DEV → TEST"
```

---

### EXAMPLES

**Правильно:**
```
AG-016: Исправить авто-передачу DEV → TEST
OWNER_SUMMARY: Задача завершена, тесты PASS
NEXT TASK: Следующая задача: AG-008
```

**Неправильно:**
```
AG-016: Fix DEV → TEST auto-handoff
OWNER_SUMMARY: Task completed, tests PASS
NEXT TASK: Next task: AG-008
```

---

### INTEGRATION

**Где применять:**
- Все user-facing сообщения
- Все policy документы
- Все DEVLOG записи

**Кто соблюдает:**
- PM, ANALYST, DEV, ARCH, TEST — все роли

---

## 13. PIPELINE_WATCHDOG

**Проблема:** Pipeline может зависнуть в TUI, а в Telegram это не видно пользователю.

**Решение:** PM отслеживает выполнение pipeline и восстанавливает при зависании.

---

### PM ОБЯЗАННОСТИ

**PM отвечает за:**
1. Отслеживание, не завис ли pipeline между стадиями
2. Проверку, был ли реально запущен следующий subagent
3. Восстановление при зависании
4. Уведомление владельца при критических проблемах

---

### STALL DETECTION RULE

**Если после завершения стадии в течение 10 секунд не стартовал следующий ожидаемый stage:**
→ Считать это **STALL**

**Ожидаемые переходы:**
```
PM → DEV (≤10 сек)
DEV → TEST (≤10 сек, по READY_FOR_TEST маркеру)
TEST → OWNER_SUMMARY (≤10 сек)
OWNER_SUMMARY → NEXT TASK (≤10 сек)
```

---

### PM RECOVERY PROCEDURE

**При обнаружении STALL:**

1. **Определить stage, где pipeline встал:**
   - Проверить последний завершённый stage
   - Проверить, запущен ли следующий subagent

2. **Попытаться продолжить автоматически:**
   - Запустить ожидаемый subagent вручную
   - Проверить, продолжился ли pipeline

3. **Если recovery не удался:**
   - Сообщить владельцу в Telegram
   - Описать проблему и предпринятые действия

---

### OWNER ALERT FORMAT

**Формат сообщения при проблеме:**

```
⚠️ Обнаружена проблема в процессе

Стадия: <PM/DEV/TEST/ARCH>
Проблема: <описание stall>
Действие PM: <что сделано для recovery>
Статус: recovered / not recovered
```

**Пример (recovered):**
```
⚠️ Обнаружена проблема в процессе

Стадия: DEV → TEST
Проблема: TEST не запущен в течение 10 сек после READY_FOR_TEST
Действие PM: Принудительный запуск TEST subagent
Статус: recovered
```

**Пример (not recovered):**
```
⚠️ Обнаружена проблема в процессе

Стадия: PM → DEV
Проблема: DEV subagent не запускается (ошибка spawn)
Действие PM: 3 попытки запуска, все failed
Статус: not recovered
Требуется: Вмешательство владельца
```

---

### LOGGING REQUIREMENT

**PM должен записать в OWNER_SUMMARY:**

```markdown
### PIPELINE_STATUS
- stalls_detected: N
- recovery_attempts: N
- recovery_success: yes/no
- systemic_issue: <описание если есть>
```

---

### INTEGRATION

**Где применять:**
- Все pipeline runs
- Все subagent spawns

**Кто соблюдает:**
- PM — основная ответственность
- TEST — валидация в POLICY_CHECK

---

## 19. BRANCH_COMPLETION_FLOW

**Проблема:** После завершения задачи (STATUS: DONE) агент не предлагает cleanup ветки → репозиторий засоряется старыми branch.

**Решение:** PM обязан проверить branch status после каждой задачи и предложить safe cleanup flow.

**Применение:** Этот раздел применяется ТОЛЬКО если задача выполнялась в SAFE_BRANCH mode (§20). Для DIRECT_MAIN cleanup не требуется.

---

### CHECKLIST ПОСЛЕ STATUS: DONE

**PM обязан проверить:**

1. **Current branch:**
   - `git branch --show-current`
   - Если `main` → cleanup не требуется

2. **Working tree:**
   - `git status --short`
   - Если есть uncommitted changes → предложить commit first

3. **Pushed to origin:**
   - `git branch -vv`
   - Если branch не pushed → предложить push first

4. **Merged to main:**
   - `git merge-base --is-ancestor <branch> main`
   - Если merged → safe to delete
   - Если not merged → предложить PR/merge

---

### CLEANUP RECOMMENDATIONS

**После проверки PM должен добавить в OWNER_SUMMARY:**

```markdown
🧹 BRANCH CLEANUP

Current branch: `<branch-name>`
Working tree: clean/dirty
Pushed to origin: yes/no
Merged to main: yes/no

Recommended action:
- [ ] Safe to delete (merged + pushed)
- [ ] Open PR first (not merged)
- [ ] Commit changes first (dirty tree)
- [ ] Keep for review (suspicious/special branch)

Commands:
```bash
# Если merged и safe to delete:
git checkout main
git pull
git branch -d <branch-name>
git push origin --delete <branch-name>

# Если не merged — open PR:
gh pr create --title "<title>" --body "<description>"
```
```

---

### BRANCH CLASSIFICATION

| тип ветки | признак | действие |
|-----------|---------|----------|
| **feature/** | feature work, bug fix | merge → delete |
| **chore/** | cleanup, refactoring | merge → delete |
| **migration/** | structure changes | merge separately, rebase features after |
| **hotfix/** | urgent production fix | merge ASAP → delete |
| **WIP/** | work in progress | keep, not ready |

---

### SUSPICIOUS BRANCHES

**Признаки suspicious branch:**

- Large deletions (>1000 lines) без явной задачи
- Удаляет policy/state/product файлы
- Не имеет связи с recent TODO.md задачами
- Based on pre-migration structure

**Действие:** Пометить как `review_required` и НЕ предлагать merge/delete без manual review.

---

### MIGRATION BRANCH RULE

**Для migration/refactor веток:**

- Держать отдельно от feature work
- Использовать `-clean` suffix для structure-only migrations
- Merge migration first
- Rebase feature branches on top of merged migration
- Delete migration branches after all features rebased

---

### SAFETY RULES

**Агент НЕ должен:**

- ❌ Самостоятельно выполнять merge без явной команды
- ❌ Самостоятельно удалять ветки без подтверждения
- ❌ Предлагать delete для WIP branches
- ❌ Игнорировать suspicious branch flags

**Агент должен:**

- ✅ Предлагать точные git-команды
- ✅ Помечать uncertain cases как `review_required`
- ✅ Напоминать о pull перед merge
- ✅ Проверять working tree перед cleanup

---

### EXAMPLE

**OWNER_SUMMARY блок:**

```markdown
---

## 🧹 BRANCH CLEANUP

**Branch:** `chore/project-structure-migration-clean`
**Status:** Ready to merge

- [x] Working tree clean
- [x] Pushed to origin
- [ ] Merged to main

**Action:** Merge to main, then delete branch

```bash
git checkout main
git pull
git merge chore/project-structure-migration-clean
git push origin main
git branch -d chore/project-structure-migration-clean
git push origin --delete chore/project-structure-migration-clean
```
```

---

## 20. GIT_WORKFLOW_MODE

**Проблема:** Workflow с обязательными ветками и PR через GitHub web UI слишком тяжёлый для solo разработки.

**Решение:** Два режима работы — DIRECT_MAIN (default) и SAFE_BRANCH (для рискованных задач).

---

### DEFAULT MODE: DIRECT_MAIN

**Применять по умолчанию для:**

- ✅ Небольших задач (<5 файлов)
- ✅ Документальных изменений (policy, docs, state)
- ✅ Bug fixes
- ✅ Feature additions, которые не ломают существующее
- ✅ Любих изменений, которые можно безопасно откатить через git revert

**Workflow:**

```
1. Работа прямо в main
2. После завершения задачи:
   - Показать diff summary
   - git add <files>
   - git commit -m "<type>: <description>"
   - git push origin main
3. Готово — никаких PR и web merge не требуется
```

**Преимущества:**

- Минимум overhead
- Нет лишней ручной работы с merge
- История остаётся линейной и понятной
- Идеально для solo workflow

---

### BRANCH MODE: SAFE_BRANCH

**Использовать ТОЛЬКО если:**

- ⚠️ Migration / структура проекта
- ⚠️ Large refactor (>10 файлов или >500 строк)
- ⚠️ Risky change (может сломать рабочее состояние)
- ⚠️ Experimental change (нужна возможность отката)
- ⚠️ Затрагивает критичные файлы (pipeline, config, core logic)

**НЕ включать автоматически без явной причины.**

**Workflow:**

```
1. Создать ветку: git checkout -b <type>/description
2. Выполнить задачу
3. Показать diff summary
4. git add + git commit
5. git push origin <branch>
6. Предложить merge options:
   - Local merge: git checkout main && git merge <branch>
   - PR через GitHub (если нужен review)
   - Rebase если нужно
7. После merge: удалить ветку (локально и remote)
```

**Merge через GitHub web UI:**

- ❌ НЕ обязателен
- ✅ Использовать только если пользователь явно хочет review flow
- ✅ Local git merge через CLI — допустимая альтернатива

---

### REQUIRED CHECKS BEFORE COMMIT/PUSH

**Перед любым commit/push агент обязан:**

1. **Показать changed files:**
   ```bash
   git status --short
   ```

2. **Показать diff/stat:**
   ```bash
   git diff --stat
   ```

3. **Убедиться что working tree ожидаемый:**
   - Нет лишних файлов
   - Нет unrelated changes
   - Нет untracked файлов, которые должны быть в .gitignore

4. **Не смешивать unrelated changes:**
   - Если в working tree есть изменения из разных задач → предложить разделить

---

### AFTER TASK COMPLETION

**После STATUS: DONE агент должен предложить:**

```markdown
📝 GIT NEXT STEP

**Mode:** DIRECT_MAIN | SAFE_BRANCH

**Current:** `<branch-name>`
**Changed:** N files, +X -Y

Options:
- [ ] Commit to main + push
- [ ] Create branch + work there
- [ ] Review changes first

Commands:
```bash
# DIRECT_MAIN
git add <files>
git commit -m "<type>: <description>"
git push origin main

# SAFE_BRANCH
git checkout -b <type>/description
git add <files>
git commit -m "<type>: <description>"
git push origin <branch>
```
```

**Агент НЕ должен:**

- ❌ Навязывать PR/web merge flow
- ❌ Требовать branch для простых задач
- ❌ Создавать ветки без объяснения причины

---

### SAFETY RULE

**Агент обязан:**

- ✅ Явно помечать, почему branch mode нужен (если применяется)
- ✅ Для solo-safe задач предлагать DIRECT_MAIN
- ✅ Проверять working tree перед commit/push
- ✅ Не смешивать unrelated changes

**Агент НЕ должен:**

- ❌ Автоматически включать branch mode без причины
- ❌ Делать risky changes в main без предупреждения
- ❌ Push'ить без показа diff summary

---

### DECISION TREE

```
Задача получена
    ↓
Это migration / large refactor / risky change?
    ↓ YES → SAFE_BRANCH (объяснить причину)
    ↓ NO
    ↓
Работа в main
    ↓
Commit + push
    ↓
Готово
```

---

### EXAMPLE: DIRECT_MAIN

```markdown
## 📝 GIT NEXT STEP

**Mode:** DIRECT_MAIN
**Changed:** 2 files, +45 -3

**Ready to commit to main:**
- `crew/AGENT_POLICY.md` — policy update
- `.gitignore` — added memory/

```bash
git add crew/AGENT_POLICY.md .gitignore
git commit -m "policy: add branch completion flow"
git push origin main
```
```

---

### EXAMPLE: SAFE_BRANCH

```markdown
## 📝 GIT NEXT STEP

**Mode:** SAFE_BRANCH (migration — 20+ files moved)
**Branch:** `chore/project-structure-migration`
**Changed:** 22 files, +1079 -39

**Why branch:** Structure migration — risky, нужно тестировать перед merge.

```bash
git checkout -b chore/project-structure-migration
git add <files>
git commit -m "chore: move project files into zones"
git push origin chore/project-structure-migration

# После тестов:
git checkout main
git merge chore/project-structure-migration
git push origin main
git branch -d chore/project-structure-migration
git push origin --delete chore/project-structure-migration
```
```

---

### INTEGRATION WITH BRANCH_COMPLETION_FLOW (§19)

**BRANCH_COMPLETION_FLOW применяется только если:**

- Задача выполнялась в SAFE_BRANCH mode
- Ветка создана, pushed, и теперь waiting for merge/delete

**Для DIRECT_MAIN:**

- cleanup не требуется (работа сразу в main)
- §19 не применяется

---

## 21. PROJECT_DOC_LANGUAGE_AND_CREW_PATH_RULE

### PROJECT_DOC_LANGUAGE_RULE

**Правило:** Все project markdown files писать на русском языке по умолчанию.

**Область применения:**
- PROJECT_CONTEXT_SUMMARY.md
- PROJECT_INDEX.md
- Все файлы в crew/
- Все файлы в state/
- Все файлы в product/
- Все файлы в architecture/
- Все файлы в docs/

**Английский допустим только для:**
- Кода и переменных
- Имён файлов/путей/идентификаторов
- Commit messages
- Технических терминов без нормального русского аналога

**Запрещено:**
- ❌ Переписывать существующие русские markdown файлы на английский
- ❌ Создавать новые project docs на английском без причины

**Если существующий файл уже на русском:**
→ Сохранять русский язык при редактировании
→ Не переводить на английский без явной команды

---

### CANONICAL_CREW_PATH_RULE

**Правило:** Canonical crew files live ONLY in crew/. Агент не должен создавать дубликаты в root.

**Canonical paths:**
| Файл | Canonical path |
|------|----------------|
| AGENTS.md | `crew/AGENTS.md` |
| HEARTBEAT.md | `crew/HEARTBEAT.md` |
| IDENTITY.md | `crew/IDENTITY.md` |
| SOUL.md | `crew/SOUL.md` |
| TOOLS.md | `crew/TOOLS.md` |
| USER.md | `crew/USER.md` |

**Запрещено:**
- ❌ Создавать или восстанавливать эти файлы в repository root
- ❌ Редактировать root-копии вместо canonical files
- ❌ Считать root-файлы валидными альтернативами

**Если в root появляются такие файлы:**
→ Считать их stray duplicates
→ Пометить как cleanup candidates
→ Предложить удалить (trash/rm)
→ При изменениях редактировать только canonical files в crew/

**Исключения:**
- Нет — эти файлы всегда должны быть в crew/

---

### TELEGRAM_PIN_BOOTSTRAP_NOTE

**Проблема:** Pinned bootstrap/source-of-truth message в Telegram может отсутствовать или устареть.

**Решение:** Агент должен пометить это как operational note, но не придумывать старые root paths.

---

#### CANONICAL BOOTSTRAP PATHS

**Source of truth — только эти файлы:**
- PROJECT_CONTEXT_SUMMARY.md
- PROJECT_INDEX.md
- state/PROJECT_STATE.md
- state/TODO.md

**Агент обязан:**
- ✅ Использовать эти файлы как bootstrap context
- ✅ Пометить operational note, если pinned message отсутствует/устарел
- ❌ **НЕ** придумывать старые root paths
- ❌ **НЕ** считать root-файлы (вне crew/) валидными

---

#### OPERATIONAL NOTE FORMAT

**Если pinned message отсутствует:**
```
📌 OPERATIONAL NOTE

Pinned bootstrap message в Telegram отсутствует или устарел.

Canonical bootstrap:
- PROJECT_CONTEXT_SUMMARY.md
- PROJECT_INDEX.md
- state/PROJECT_STATE.md
- state/TODO.md

Рекомендация: Закрепить актуальный message с навигацией.
```

---

### INTEGRATION

**PROJECT_DOC_LANGUAGE_RULE применяется:**
- При создании новых markdown файлов
- При редактировании существующих
- При bootstrap сессии (PROJECT_CONTEXT_SUMMARY.md)

**CANONICAL_CREW_PATH_RULE применяется:**
- При старте сессии (не восстанавливать root-дубликаты)
- При редактировании crew files
- При cleanup working tree

---

_Версия: 1.22 | Создано: 2026-03-27 | Updated: PM_EXECUTION_GATE, EXECUTION_COMPLETION_RULE, DEPLOY_STATUS_RULE (Docker definition), MEMORY_WRITE_RULE, POST_TASK_SANITY_CHECK, PROJECT_DOC_UPDATE_SCOPE, LANGUAGE_OUTPUT_DISCIPLINE, TELEGRAM_PIN_BOOTSTRAP_NOTE, ORCHESTRATION_FLOW, SUBAGENT_RESULT_RETURN_
