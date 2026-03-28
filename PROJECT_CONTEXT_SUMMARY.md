# PROJECT CONTEXT SUMMARY

**Bootstrap-файл для старта новой LLM-сессии.**

---

## НАЗНАЧЕНИЕ

Этот файл — ваша точка входа при старте сессии. Прочитайте его сначала, затем PROJECT_INDEX.md, затем только файлы, релевантные вашей текущей задаче. Держите этот файл коротким и регулярно обновляйте.

---

## ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА

**Проект:** Agon Arena — Telegram-бот для практики управленческих поединков

**Статус:** MVP в фазе активной полировки

**Текущая фаза:** Post-migration cleanup + стабилизация функциональности

**Что важно сейчас:**
- Миграция структуры завершена (2026-03-28)
- Все файлы организованы по зонам: crew/, state/, product/, architecture/, docs/
- Git workflow упрощён до DIRECT_MAIN по умолчанию
- Core duel-flow стабилен и протестирован

---

## НАВИГАЦИЯ

| Зона | Назначение |
|------|---------|
| **PROJECT_INDEX.md** | Карта проекта + навигация по зонам |
| **crew/** | Policy, workflow, role files (AGENT_POLICY.md, SOUL.md, etc.) |
| **state/** | Текущее состояние, backlog, devlog (TODO.md, PROJECT_STATE.md, DEVLOG.md) |
| **product/** | Product docs (PROJECT.md, ACCEPTANCE.md, USER_FLOW.md) |
| **architecture/** | Структура системы (ARCHITECTURE.md) |
| **docs/** | Reference docs, baselines, analysis |
| **memory/** | Daily memory notes (исторические, локальные) |
| **app/** | Application code |

---

## ПРАВИЛО СТАРТА СЕССИИ

1. **Начните здесь** — прочитайте этот файл
2. **Прочитайте PROJECT_INDEX.md** — поймите структуру проекта
3. **Читайте только релевантное** — используйте зоны для поиска нужных файлов
4. **Предпочитайте текущее состояние** — state/* файлы важнее исторических заметок при конфликтах

---

## ТЕКУЩИЙ ФОКУС

**Завершено:**
- ✅ Миграция структуры (все файлы в целевых зонах)
- ✅ Git workflow policy упрощён (DIRECT_MAIN по умолчанию)
- ✅ Core duel-flow стабилен (тесты проходят)
- ✅ Telegram UX работает (scenario picker, round buttons, voice input)

**Срочные структурные изменения не требуются:**
- Policy актуален (v1.19)
- Структура стабильна
- Нет открытых P0 багов

**Следующие логичные классы работ:**
- Feature backlog (duel history UX, улучшения scoring rubric)
- Полировка + refinements по user feedback
- Technical debt cleanup (если выявлен)

---

## ACTIVE_POLICY_HIGHLIGHTS

**Операционные правила (из crew/AGENT_POLICY.md):**

1. **PM = single entry/exit** — вся координация через роль PM
2. **THINKING_MODE_CONTROL** — режимы EXECUTION (default), ANALYSIS, FREE
3. **DIRECT_MAIN git workflow** — работа в main по умолчанию, commit + push после задачи
4. **SAFE_BRANCH только для рискованных работ** — migration, large refactor, experimental changes
5. **Mandatory documentation updates** — обновление state/* файлов после значимых изменений
6. **Chinese stack priority** — ModelStudio модели по умолчанию (qwen3.5-plus, qwen3-coder-plus)

---

## ЗАМЕТКИ

- **memory/*.md** — исторические/локальные continuity notes — читайте для контекста, не treat as source of truth
- **PROJECT_CONTEXT_SUMMARY.md** должен оставаться коротким — обновляйте этот файл каждые несколько сессий
- **Если сомневаетесь** — проверьте crew/AGENT_POLICY.md для operational rules, state/TODO.md для backlog

---

**Updated:** 2026-03-28  
**Version:** 2.1 (russian translation)
