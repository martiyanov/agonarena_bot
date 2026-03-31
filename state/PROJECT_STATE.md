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
- **AG-006:** Commit and push validated release — DONE (2026-03-31)
  - **Commit:** aa6f170 — "feat: inline round button + pipeline improvements"
  - **Tests:** 22/22 PASS + 4/4 E2E PASS
  - **Deploy:** Production DEPLOYED ✅
- **AG-010:** Clean project git diff — DONE (2026-03-31)
  - **Result:** 9 файлов закоммичено, мусор исключён
- **AG-017:** Inline-кнопка "Завершить раунд" — DONE (2026-03-29)
  - **Scope:** Inline кнопка в сообщениях дуэли, 6 состояний Duel.status
  - **Tests:** 22/22 PASS
- **AG-018:** Исправить callback ошибку — DONE (2026-03-29)
  - **Scope:** Фикс callback_data формата для inline кнопки
- **AG-019:** Убрать дублирование "🎲 Случайный" — DONE (2026-03-29)
  - **Scope:** Кнопка только в пикере, убрана из меню
- **AG-020:** Объединить два сообщения при дуэли — DONE (2026-03-29)
  - **Scope:** Одно сообщение с inline кнопкой вместо двух
- **AG-021:** Улучшить форматирование "Поединок начался" — DONE (2026-03-29)
  - **Scope:** Чёткое разделение блоков информации

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
- **AG-016:** Pipeline orchestration fixed (auto-test spawner + fallback timer)
