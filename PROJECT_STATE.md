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
- Telegram UX acceptance for scenario picker / round-end flow on production

## Current blocker
- Need manual Telegram acceptance to confirm the deployed runtime matches the intended UX in the real client

## Next real step
- Manually verify in Telegram:
  1. `🎯 Выбрать сценарий`
  2. list of 10 scenarios
  3. inline button `Начать сценарий`
  4. normal duel start
  5. `🏁 Завершить раунд` flow

## Notes
- duel-flow tests subtask is complete
- cleanup of temporary debug diff is complete
- runtime mismatch issue was found and resolved via local container redeploy
