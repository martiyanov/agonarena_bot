# PIPELINE_BASELINE_2026-03-27.md

**Snapshot Date:** 2026-03-27  
**Version:** 1.0  
**Purpose:** Baseline snapshot текущей системы разработки (без изменения кода приложения)

---

## ACTIVE ROLES

| Роль | Статус | Когда |
|------|--------|-------|
| **PM** | ✅ Active | Всегда (координация) |
| **ANALYST** | ✅ Active | On-demand (UX, A/B, product uncertainty) |
| **DEV** | ✅ Active | Всегда (реализация) |
| **TEST** | ✅ Active | Всегда (валидация) |
| **ARCH** | ✅ Active | On-demand (архитектура, state, refactor) |

---

## ROLE → MODEL MAPPING

| Роль | Модель | Почему |
|------|--------|--------|
| **PM** | `modelstudio/qwen3.5-plus` | Баланс качества и скорости |
| **ANALYST** | `modelstudio/qwen3.5-plus` | UX решения не требуют max модели |
| **DEV** | `modelstudio/qwen3-coder-plus` | Специализированная coding модель |
| **TEST** | `modelstudio/qwen3-coder-plus` | Тесты и валидация кода |
| **ARCH** | `modelstudio/qwen3-max-2026-01-23` | Сильный reasoning для системных решений |

---

## DELIVERY POLICY

### Target Rule
- **PM questions:** Доставлять в parent session (откуда пришёл запрос)
- **OWNER_SUMMARY:** Доставлять в originating session
- **Hardcoded sessionKey:** ❌ Запрещён

### Implementation
```typescript
sessions_send({
  message: `📋 PM QUESTION:\n${content}`
  // sessionKey не указан → parent session автоматически
});
```

### PM Question Rate Control (Anti-Noise)

| Limit | Value |
|-------|-------|
| Максимум за шаг pipeline | 1 вопрос |
| Максимум на задачу | 3 вопроса |
| При превышении | Агрегировать в batch |

### Batch Format
```
📋 Нужно уточнить:
1. ...
2. ...
3. ...
```

---

## DECISION WITHOUT QUESTION POLICY

**PM НЕ задаёт вопрос если решение есть в:**

| Источник | Пример |
|----------|--------|
| AGENT_POLICY.md | Зафиксированные правила |
| SUBAGENT_WORKFLOW.md | Pipeline правила |
| TODO.md | Приоритеты задач |
| PROJECT_STATE.md | Текущее состояние |
| ACCEPTANCE.md | Протоколы приёмки |
| DEVLOG.md / PROMPTS.md | Ранее зафиксированные decisions |

**Precedence:**
```
1. Existing decision (DEVLOG.md, PROMPTS.md, PROJECT_STATE.md)
2. Policy (AGENT_POLICY.md, TODO.md, ACCEPTANCE.md)
3. Ask user (только если нет 1 и 2)
```

---

## AUTO ROLE SELECTION

### ROLE_DECISION_ENGINE

**INPUT:**
- `task_description`
- `changed_files`
- `estimated_scope`
- `task_type` (bug / UX / feature / refactor)

**OUTPUT:**
- `use_analyst: yes/no`
- `use_arch: yes/no`

### ANALYST = yes если (любое из):
- ✅ `task_type == UX`
- ✅ Contains: "вариант", "layout", "UX", "выбор", "A/B"
- ✅ Ambiguity present

### ARCH = yes если (любое из):
- ✅ `estimated_scope > 100 LOC`
- ✅ `changed_files > 1`
- ✅ Contains: "refactor", "архитектура", "state", "concurrency"
- ✅ Integration / external risk

### Pipeline
```
PM → [AUTO: ANALYST?] → DEV → [AUTO: ARCH?] → TEST → OWNER_SUMMARY
```

### Manual Override
```
[OVERRIDE: force ANALYST]
[OVERRIDE: force ARCH]
[OVERRIDE: skip ANALYST]
[OVERRIDE: skip ARCH]
```

---

## COST_CONTROL_POLICY

### ANALYST Limits
| Правило | Значение |
|---------|----------|
| Базовый лимит | 1 вызов на задачу |
| Повторный вызов | Только с `[OVERRIDE: force ANALYST]` |

### ARCH Limits
| Правило | Значение |
|---------|----------|
| Базовый лимит | 1 вызов на задачу |
| Повторный вызов | `[OVERRIDE: force ARCH]` или TEST FAIL с architectural concern |

### Downgrade Rule (ARCH запрет)
**ARCH запрещён если:**
- `changed_files == 1` (single-file)
- `estimated_scope < 100 LOC`

**В этом случае:** Использовать только DEV + TEST

### Cost Logging
```markdown
### ROLE_COST

| Метрика | Значение |
|---------|----------|
| analyst_calls | N |
| arch_calls | N |
| cost_control_triggered | yes/no |
```

---

## VALIDATED EXAMPLES

### Example 1 — Simple UI Text Fix
**Сценарий:** "Поправить текст одной кнопки в Telegram UI"

| INPUT | Value |
|-------|-------|
| task_type | bug |
| changed_files | 1 |
| estimated_scope | <10 LOC |

| Роль | Решение | Почему |
|------|---------|--------|
| ANALYST | no | Нет UX неопределённости |
| ARCH | no | Downgrade: single-file, <100 LOC |

**cost_control_triggered:** yes  
**Pipeline:** PM → DEV → TEST

---

### Example 2 — Duel State Machine Refactor
**Сценарий:** "Рефакторинг state machine поединка, 4 файла, >100 LOC"

| INPUT | Value |
|-------|-------|
| task_type | refactor |
| changed_files | 4 |
| estimated_scope | >100 LOC |

| Роль | Решение | Почему |
|------|---------|--------|
| ANALYST | no | Нет UX неопределённости |
| ARCH | yes | Scope >100 LOC, 4 файла, state machine |

**cost_control_triggered:** no  
**Pipeline:** PM → DEV → ARCH → TEST

---

## CURRENT BACKLOG

| Task | Title | Priority | Status |
|------|-------|----------|--------|
| **AG-006** | Commit and push validated release | P0 | **TODO (NEXT)** |
| AG-008 | Normalize judge output by round | P1 | TODO |
| AG-009 | Route feedback to owner channel | P1 | TODO |
| AG-010 | Clean project git diff before release | P1 | TODO |

### Recently Closed
| Task | Title | Closed Date |
|------|-------|-------------|
| AG-005 | Manual production acceptance | 2026-03-27 |
| AG-007 | Scenario picker layout improved | 2026-03-27 |
| AG-011 | Voice message breaks duel-flow | 2026-03-27 |

---

## KNOWN_WORKING_STATE

### ✅ Confirmed Working

| Component | Status | Evidence |
|-----------|--------|----------|
| **Telegram group routing** | ✅ Working | Messages delivered to -4998914548 |
| **PM question delivery** | ✅ Working | Dynamic parent session delivery (hardcoded removed) |
| **Multi-model subagents** | ✅ Working | sessions_spawn with model override tested |
| **AG-005** | ✅ Closed | Telegram acceptance PASS (2026-03-27) |
| **AG-006** | ⏳ TODO | Release commit pending |
| **AG-007** | ✅ Closed | Variant B selected, deployed, tested |
| **AG-011** | ✅ Closed | Voice fix implemented, tests 6/6 PASS |

### Pipeline Health

| Check | Status |
|-------|--------|
| PM → DEV → TEST flow | ✅ Working |
| ANALYST on-demand | ✅ Configured |
| ARCH on-demand | ✅ Configured |
| Auto role selection | ✅ Validated |
| Cost control | ✅ Enforced |
| Delivery policy | ✅ Fixed (no hardcoded sessionKey) |
| Decision without question | ✅ Enforced |
| PM rate control | ✅ Enforced |

---

## FILES REFERENCE

| File | Purpose |
|------|---------|
| `AGENT_POLICY.md` | Source of truth для pipeline и delivery rules |
| `SUBAGENT_WORKFLOW.md` | Роли, триггеры, validated examples |
| `TODO.md` | Backlog и статусы задач |
| `PROJECT_STATE.md` | Текущее состояние проекта |
| `DEVLOG.md` | История решений и изменений |
| `PROMPTS.md` | Архив промтов (если существует) |
| `ACCEPTANCE.md` | Протоколы ручной приёмки |

---

## SNAPSHOT NOTES

**Created:** 2026-03-27  
**Snapshot includes:**
- ✅ Active roles and model mapping
- ✅ Delivery policy (fixed, no hardcoded sessionKey)
- ✅ PM rate control (anti-noise)
- ✅ Decision without question policy
- ✅ Auto role selection (ROLE_DECISION_ENGINE)
- ✅ Cost control policy (ANALYST/ARCH limits)
- ✅ Validated examples (simple vs complex tasks)
- ✅ Current backlog state

**Next task:** AG-006 — Commit and push validated release after manual PASS

---

_Это baseline snapshot системы разработки. Не изменяет код приложения._
