# Agon Arena Bot

Telegram-бот для практики управленческих поединков.

## Что делает бот

- только текстовые поединки
- человек против AI
- формат экспресс-поединка
- 2 раунда
- во втором раунде — смена ролей
- 3 судьи:
  - собственник
  - команда
  - отправляющий на переговоры
- button-first интерфейс
- сценарий при быстром старте выбирается автоматически из активных
- пользовательский ход можно отправить текстом или голосовым сообщением
- на каждый раунд действует таймер 3 минуты

## Что уже работает

- FastAPI-приложение с health endpoint
- Telegram webhook на aiogram
- SQLite-хранилище
- сидирование сценариев из `seeds/scenarios.json`
- запуск поединка по сценарию
- 2 раунда со сменой ролей
- сохранение ходов пользователя и AI в `duel_messages`
- переход к следующему раунду
- завершение поединка и запуск 3 судей
- вывод результатов последнего поединка в Telegram и через API
- OpenAI-compatible LLM integration для оппонента и судей, с fallback на rule-based логику если ключ не задан

## Технический профиль текущей версии

- Python
- FastAPI
- aiogram
- SQLite
- без Redis на старте
- один инстанс приложения на VDS
- запуск только через Docker / docker-compose
- данные и sqlite-файл сохраняются через volume

## Основные API endpoints

- `GET /health`
- `GET /api/scenarios`
- `POST /api/duels/start/{scenario_code}`
- `GET /api/duels/{duel_id}`
- `POST /api/duels/{duel_id}/turn`
- `POST /api/duels/{duel_id}/next-round`
- `POST /api/duels/{duel_id}/finish`

## Telegram flow

1. `/start`
2. `⚔️ Начать поединок`
3. отправка текстовых или голосовых реплик
4. `⏭️ Раунд 2`
5. снова ходы
6. `🏁 Завершить`
7. итоговый вердикт в сообщении бота

Подробный сценарий: `USER_FLOW.md`.

## LLM / промпты

- промпт оппонента: `app/prompts/opponent.md`
- промпт судей: `app/prompts/judges.md`

Если заданы `OPENAI_API_KEY`, `OPENAI_BASE_URL` и `LLM_MODEL`, бот использует OpenAI-compatible API.
Если ключа нет, бот остаётся работоспособным на fallback-логике.
