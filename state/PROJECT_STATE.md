# PROJECT_STATE.md

## Product
- Product: Agon Arena Bot
- Interface: Telegram bot
- Version stage: MVP in active polishing
- Core mode: human vs AI
- Duel format: 2 rounds + role swap + 3 judges
- Main storage: SQLite
- Runtime: single Docker container on VDS

## Runtime facts
- Local tests and runtime live on the same host
- GitHub is storage, not deployment source
- Production acceptance happens manually in Telegram after local redeploy

## What is working now
- FastAPI app with webhook and health endpoint
- aiogram Telegram layer
- scenario seeds from `seeds/scenarios.json`
- duel lifecycle API
- 2-round duel flow with role swap
- finish + judges pipeline
- text and voice user input
- stable writable test DB isolation for duel-flow tests
- contract checks for repeat finish / invalid next-round
- Telegram UX button `🏁 Завершить раунд`
- menu button `🎯 Выбрать сценарий`
- scenario picker MVP in code and deployed runtime

## Verified evidence
- canonical test command:
  `PYTHONPATH=. ./.venv/bin/pytest tests/test_duel_flow.py -q`
- latest known green result:
  `6 passed in 57.51s`
- runtime was redeployed and checked from inside container

## Current release policy
1. Change code in workspace
2. Run local pytest
3. If tests pass -> local deploy to `agonarena-bot-app`
4. Verify runtime matches workspace
5. Manual acceptance in Telegram on production
6. Only after manual PASS -> commit and push to GitHub

## Current active task
- None (all P0/P1 tasks complete)

## Latest closures
- **AG-009:** Feedback routing to owner — DONE (2026-03-28)
  - **Scope:** feedback_owner_user_id config, message forwarding handler
  - **Files updated:** app/config.py, app/bot/handlers/menu.py, state/TODO.md
- **AG-007:** Telegram acceptance PASS (2026-03-27) — scenario picker message layout improved
  - **UX_DECISION:** Variant B confirmed — цифры без emoji
  - **Scope:** delivery policy fixed, Docker implementation applied, user acceptance confirmed
  - **Files updated:** TODO.md, PROJECT_STATE.md

## Next real step
- Backlog: AG-008 (judge round breakdown), AG-015 (token analysis), AG-012/013/014 (backlog)
- Blockers: None

## Notes
- duel-flow tests subtask is complete
- cleanup of temporary debug diff is complete
- runtime mismatch issue was found and resolved via local container redeploy
- **AG-011 voice fix:** confirmed via `tests/test_voice_routing.py` 6/6 PASS
- **AG-006 release:** committed & pushed (`c722b98` on `feature/menu-ux-refresh`)
- **Acceptance protocol:** created `product/ACCEPTANCE.md` for reproducible manual testing

## Token Efficiency Analysis (AG-015)

**Идея:** Оценить, где теряются токены в pipeline разработки задач.

**Scope для анализа:**
- PM ↔ ANALYST ↔ DEV ↔ ARCH ↔ TEST — расход токенов на каждую роль
- Delivery в Telegram — OWNER_SUMMARY, PM QUESTION, NEXT TASK
- Лишние вопросы / дублирование / verbose formatting
- Subagent overhead — сколько токенов тратится на координацию

**План:**
1. Сначала analysis phase (без оптимизаций)
2. Потом решение: отдельная роль или использование ANALYST

**Статус:** Задача добавлена в TODO.md (AG-015, P1)

---

## Pipeline Orchestration Bug (AG-016)

**Проблема:** Pipeline не переходит автоматически DEV → TEST.

**Факты:**
- DEV завершился (READY_FOR_TEST: yes)
- TEST subagent не был spawned автоматически
- Pipeline завис, требовался manual запуск TEST
- AG-009 TEST пришлось запускать вручную

**Текущее поведение:**
```
PM → DEV → [STALL] → (manual trigger) → TEST → OWNER_SUMMARY
```

**Ожидаемое поведение:**
```
PM → DEV → [auto] → TEST → OWNER_SUMMARY
```

**Статус:** Задача добавлена в TODO.md (AG-016, P0)
