# Agon Arena — ARCHITECTURE

## High-level layers

### 1. Telegram layer
Отвечает за:
- `/start`
- главное меню
- выбор сценария
- запуск поединка
- ходы пользователя
- round-end / finish UX
- показ итогов

Технология:
- aiogram
- webhook endpoint внутри FastAPI

### 2. Application layer
Отвечает за:
- создание `Duel`
- создание `DuelRound`
- смену ролей
- сохранение сообщений
- переходы состояний
- завершение поединка
- запуск judge pipeline

Основные сервисы:
- `ScenarioService`
- `DuelService`
- `OpponentService`
- `JudgeService`
- `RoundTimerService`

### 3. Storage layer
Текущая версия использует SQLite.

Хранит:
- сценарии
- поединки
- раунды
- сообщения
- результаты судей

### 4. AI layer
Состоит из двух независимых частей:
- AI-оппонент
- 3 виртуальных судьи

Используется OpenAI-compatible API с fallback-логикой.

## Main runtime flow
1. Пользователь открывает Telegram-бота.
2. Бот показывает reply keyboard.
3. Пользователь выбирает сценарий или другой режим старта.
4. Backend создаёт duel и 2 раунда.
5. Идёт раунд 1.
6. Пользователь завершает раунд.
7. Идёт раунд 2 со сменой ролей.
8. Пользователь завершает поединок.
9. Судьи выдают вердикт.

## Current UX architecture decisions
- Главное меню — reply keyboard.
- Выбор сценария — сообщение в чате + inline buttons.
- Старт конкретного сценария использует существующий duel-flow.
- Внутри поединка основная action-кнопка: `🏁 Завершить раунд`.

## Infra
- один Docker image
- один runtime container: `agonarena-bot-app`
- deploy локально на VDS
- SQLite mounted через volume `./data:/app/data`

## Testing and release
- Source of truth for duel-flow regression: `tests/test_duel_flow.py`
- Canonical command:
  `PYTHONPATH=. ./.venv/bin/pytest tests/test_duel_flow.py -q`
- Deploy only after green tests
- GitHub push only after successful production manual acceptance

## Constraints
- single instance only
- no Redis
- no PostgreSQL
- no pagination for scenarios in MVP
- no separate admin panel in current stage
