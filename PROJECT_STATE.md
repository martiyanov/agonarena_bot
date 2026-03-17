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
  - JudgeResult
- sqlite tables are created on startup

### In progress
- service layer for duel lifecycle
- scenario loading / seed strategy
- first usable duel creation flow

### Next
1. add duel service
2. create round generation logic
3. define judge pipeline contract
4. add first scenario seeds
5. add telegram start / menu flow

## Local commits so far
- 05bad53 chore: initialize agonarena bot scaffold
- ba54345 docs: simplify mvp stack to sqlite
- 32da835 docs: require docker-first mvp setup
- 7edce4b feat: add docker-first runnable app skeleton
- 75f8a56 feat: add core duel domain models
