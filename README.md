# Agon Arena Bot

Telegram-бот для практики управленческих поединков.

## Что уже умеет

- 2-раундовый поединок: человек против AI
- смена ролей во втором раунде
- 3 AI-судьи после завершения
- выбор готового сценария из списка
- случайный сценарий
- пользовательский сценарий из свободного описания
- текстовые и голосовые реплики
- SQLite-хранилище
- Docker runtime на одном хосте

## Telegram UX сейчас

- `/start`
- `🎯 Выбрать сценарий`
- бот присылает список из 10 готовых сценариев
- у каждого сценария inline-кнопка `Начать сценарий`
- внутри поединка основная action-кнопка: `🏁 Завершить раунд`

## Основной duel-flow

1. выбрать сценарий
2. пройти раунд 1
3. завершить раунд
4. пройти раунд 2 со сменой ролей
5. завершить раунд
6. получить вердикт судей

## API

- `GET /health`
- `GET /api/scenarios`
- `POST /api/duels/start/{scenario_code}`
- `GET /api/duels/{duel_id}`
- `POST /api/duels/{duel_id}/turn`
- `POST /api/duels/{duel_id}/next-round`
- `POST /api/duels/{duel_id}/finish`

## Tests

Canonical command:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_duel_flow.py -q
```

Последний подтверждённый результат:
- `6 passed in 57.51s`

## Deploy flow

1. изменить код в workspace
2. прогнать pytest
3. если тесты зелёные — локально пересобрать и перезапустить `agonarena-bot-app`
4. проверить, что runtime совпадает с workspace
5. пройти manual acceptance в Telegram на production
6. только после этого делать commit и push в GitHub
