# Agon Arena — ARCHITECTURE

## Architecture

### 1. Telegram layer
Отвечает за:
- `/start`
- главное меню
- выбор сценария
- старт поединка
- показ результатов

Технология:
- aiogram
- webhook endpoint внутри FastAPI

### 2. Application layer
Отвечает за:
- создание поединка
- создание 2 раундов
- смену ролей
- сохранение состояния
- подготовку результата для судей

Основные сервисы:
- `ScenarioService`
- `DuelService`
- позже: `JudgeService`, `OpponentService`

### 3. Storage layer
Текущая версия использует SQLite.

Хранит:
- сценарии
- поединки
- раунды
- результаты судей

### 4. AI layer
Будет состоять из двух независимых логик:
- AI-оппонент
- 3 виртуальных судьи

Первая версия использует один LLM provider через OpenAI-compatible API.

## Основной flow

1. Пользователь приходит в Telegram-бота.
2. Бот показывает главное меню.
3. Пользователь выбирает сценарий.
4. Backend создаёт `Duel` и 2 `DuelRound`.
5. Проходит раунд 1.
6. Роли меняются.
7. Проходит раунд 2.
8. 3 judge pipelines выносят вердикты.
9. Бот показывает итог.

## Инфраструктура

- Docker / docker-compose only
- один контейнер приложения
- SQLite в volume
- health endpoint `/health`

## Ограничения текущей версии

- только текст
- только человек vs AI
- без аудио
- без Redis
- без PostgreSQL
- без multi-user battle rooms
