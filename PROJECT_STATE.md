# PROJECT_STATE.md

## Product frame
- Product: Agon Arena Bot
- Interface: Telegram bot
- MVP v1: text only
- Duel format: express management duel
- Opponent mode in v1: human vs AI
- Rounds: 2
- Role swap: yes, in round 2
- Judges: 3
  - owner
  - team
  - sending_to_negotiation

## Technical frame
- Stack: Python + FastAPI + aiogram
- Storage: SQLite
- Infra: Docker / docker-compose only
- Current app mode: single instance on VDS

## Progress
### Done
- repository cloned
- docker-first runnable skeleton added
- health endpoint working in container
- core domain models added:
  - Scenario
  - Duel
  - DuelRound
  - DuelMessage
  - JudgeResult
- sqlite tables are created on startup
- scenario seed strategy implemented via `seeds/scenarios.json`
- duel lifecycle service implemented
- round generation logic implemented
- telegram start / menu flow implemented
- round message persistence implemented
- next round transition implemented
- duel finish + judge pipeline implemented
- API endpoints added for duel lifecycle
- prompts added for AI opponent and judges
- LLM-first / fallback execution added for opponent and judges

### In progress
- light cleanup / test pass

### Next
1. add automated tests for duel lifecycle
2. improve judge heuristics and scoring rubric
3. improve telegram UX with scenario selection buttons instead of code entry
4. add richer duel analytics and history

## Local commits so far
- 05bad53 chore: initialize agonarena bot scaffold
- ba54345 docs: simplify mvp stack to sqlite
- 32da835 docs: require docker-first mvp setup
- 7edce4b feat: add docker-first runnable app skeleton
- 75f8a56 feat: add core duel domain models
