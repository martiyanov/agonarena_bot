# Архитектурный анализ: Inline-кнопка "Завершить раунд" (AG-017)

**Дата:** 2026-03-29  
**Архитектор:** Subagent (modelstudio/qwen3-max-2026-01-23)  
**Статус:** ✅ Рекомендовано к реализации (с изменениями)

---

## 📊 Резюме

**Финальная рекомендация:** ✅ **ДЕЛАТЬ, с изменениями**

UX-проблема реальная — кнопка в reply keyboard действительно скрывается. Inline-кнопки решают проблему видимости. Архитектурные риски управляемые при реализации рекомендаций.

---

## 🔴 Архитектурные риски (по приоритету)

### HIGH: Race condition между таймером и callback

**Проблема:** RoundTimerService завершает раунд в фоне. Пользователь может нажать inline-кнопку в тот же момент.

**Сценарий:**
```
T0: Таймер просыпается, проверяет seconds_left = 0
T1: Пользователь нажимает "Завершить раунд"
T2: Таймер вызывает complete_round() → round.status = "finished"
T3: Callback handler проверяет round.status → уже "finished"
T4: Пользователь получает "Раунд уже завершён"
```

**Решение:** Добавить атомарный transition flag в DuelService:
```python
async def complete_round(self, duel: Duel, round_obj: DuelRound, initiated_by: str = "timer") -> bool:
    if round_obj.status == "finished":
        return False  # Уже завершено
    round_obj.status = "finished"
    # ... остальная логика
    return True  # Успешно завершено
```

---

### HIGH: Старые inline-кнопки остаются активными

**Проблема:** Inline-кнопки в Telegram не инвалидируются автоматически. После перехода в раунд 2 кнопки раунда 1 всё ещё работают.

**Решение:** В callback handler добавить проверку:
```python
if parsed_round_no != duel.current_round_number:
    await callback.answer("Эта кнопка уже неактуальна", show_alert=True)
    return
```

---

### MEDIUM: Конфликт с STT processing

**Проблема:** В `process_voice_turn()` есть окно между "🎤 Голосовое получено" и "🤖 Ответ готов". Если пользователь нажмёт inline-кнопку в этот момент — возможна гонка.

**Решение:** Расширить `ACTION_IN_PROGRESS_USERS` на inline callbacks ИЛИ добавить флаг `is_processing_turn` в Duel/DuelRound.

---

### MEDIUM: Отсутствие дедупликации callback

**Проблема:** Telegram может доставить один callback дважды (retry при таймауте).

**Решение:** Добавить `processed_callbacks` set с TTL (5 мин) или использовать `callback.answer()` как ack.

---

### LOW: Визуальный шум от кнопок

**Проблема:** Вариант A (кнопка на каждом сообщении AI) создаст 10-20 кнопок в длинном раунде.

**Решение:** Документировать как известное ограничение MVP. В Варианте B решить через редактирование последнего сообщения.

---

## 🔄 Рекомендации по state machine

### Текущие состояния (из кода):
```python
# Duel.status
"draft" → "in_progress" → "ready" → "judging" → "finished"

# DuelRound.status
"pending" → "in_progress" → "finished"
```

### ✅ Вывод: Текущих состояний НЕ достаточно

**Рекомендация:** Добавить в `Duel.status`:
```python
VALID_DUEL_STATUSES = {
    "idle",              # Нет активной дуэли
    "round_1_active",    # Раунд 1 идёт, можно завершить
    "round_1_processing", # STT/AI в процессе
    "round_1_transition", # Переход к раунду 2
    "round_2_active",    # Раунд 2 идёт, можно завершить
    "round_2_processing", # STT/AI в процессе
    "round_2_transition", # Переход к финалу
    "judging",           # Судьи работают
    "finished",          # Завершено
}
```

**Миграция БД:** Не требуется — статусы хранятся как `String(32)`.

---

## 🔒 Рекомендации по concurrency

### 3.1. Глобальный lock на дуэль

**Решение:** Добавить asyncio.Lock per duel_id:
```python
_duel_locks: dict[int, asyncio.Lock] = {}

async def get_duel_lock(duel_id: int) -> asyncio.Lock:
    if duel_id not in _duel_locks:
        _duel_locks[duel_id] = asyncio.Lock()
    return _duel_locks[duel_id]

# В callback handler:
async with await get_duel_lock(duel_id):
    # Все проверки и transition атомарно
```

**Очистка:** Удалять lock после `finished` статуса.

---

### 3.2. Расширить ACTION_IN_PROGRESS_USERS

```python
# В начале callback handler:
if user_id in ACTION_IN_PROGRESS_USERS:
    await callback.answer("⏳ Пожалуйста, дождитесь завершения предыдущего действия", show_alert=True)
    return
ACTION_IN_PROGRESS_USERS.add(user_id)
try:
    # Обработка
finally:
    ACTION_IN_PROGRESS_USERS.discard(user_id)
```

---

### 3.3. Timer должен проверять перед отправкой сообщения

```python
await duel_service.complete_round(duel, round_obj)
await session.commit()

# Проверка: не завершил ли пользователь вручную
if duel.status == "finished":
    logger.info("Duel finished by user, skipping timeout message")
    return
```

---

## 🎯 Рекомендации по callback flow

### 4.1. Структура callback data с versioning

```python
callback_data = f"duel:v1:end:{duel_id}:{round_no}"
```

**Handler:**
```python
@router.callback_query(F.data.startswith("duel:v1:end:"))
async def handle_end_duel_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректный формат кнопки", show_alert=True)
        return
    
    duel_id = int(parts[2])
    round_no = int(parts[3])
```

---

### 4.2. Порядок проверок в handler (6 проверок + concurrency)

```python
async def handle_end_duel_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # 0. Глобальная блокировка (concurrency)
    if user_id in ACTION_IN_PROGRESS_USERS:
        await callback.answer("⏳ Действие уже выполняется", show_alert=True)
        return
    
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        
        # 1. Есть ли активная дуэль
        duel = await duel_service.get_latest_duel_for_user(session, user_id)
        if duel is None:
            await callback.answer("Нет активной дуэли", show_alert=True)
            return
        
        # 2. Совпадает ли duel_id (защита от старых кнопок)
        if duel.id != parsed_duel_id:
            await callback.answer("Эта кнопка от старой дуэли", show_alert=True)
            return
        
        # 3. Совпадает ли раунд
        if duel.current_round_number != parsed_round_no:
            await callback.answer("Эта кнопка уже неактуальна", show_alert=True)
            return
        
        # 4. Не finished/transitioning ли дуэль
        if duel.status in ("finished", "judging", "round_1_transition", "round_2_transition"):
            await callback.answer("Поединок уже завершается", show_alert=True)
            return
        
        # 5. Не идёт ли STT/AI processing
        if "processing" in duel.status:
            await callback.answer("⏳ Дождитесь обработки текущего сообщения", show_alert=True)
            return
        
        # 6. Актуальный статус раунда
        round_obj = await duel_service.get_round(session, duel.id, parsed_round_no)
        if round_obj.status != "in_progress":
            await callback.answer("Раунд уже завершён", show_alert=True)
            return
        
        # ✅ Все проверки пройдены — выполняем transition
        ACTION_IN_PROGRESS_USERS.add(user_id)
        try:
            await _complete_round_or_finish(duel, round_obj, callback)
        finally:
            ACTION_IN_PROGRESS_USERS.discard(user_id)
```

---

### 4.3. Интеграция с существующими handlers

**Конфликт:** Существующий `@router.callback_query(F.data == "end_round")` конфликтует с новым `duel:v1:end:{duel_id}:{round_no}`.

**Решение:** 
1. Удалить старый `end_round` handler
2. Обновить `_process_end_round()` для вызова из нового callback

---

## 📝 Дополнительные требования

### 5.1. Логирование

```python
logger.info(
    "callback:end_round",
    extra={
        "user_id": user_id,
        "duel_id": duel_id,
        "round_no": round_no,
        "duel_status": duel.status,
        "round_status": round_obj.status,
        "result": "accepted" | "rejected:reason",
    }
)
```

### 5.2. Метрики (опционально)

Если есть Prometheus — добавить counter/histogram для callback.

---

## ✅ DoD для разработчика (дополнение к UX DoD)

### Технические требования

- [ ] **State machine:** Добавить 6 новых состояний в Duel.status (`round_1_active`, `round_1_processing`, `round_1_transition`, `round_2_active`, `round_2_processing`, `round_2_transition`)
- [ ] **Concurrency:** Реализовать `get_duel_lock(duel_id)` в DuelService
- [ ] **Callback versioning:** Использовать `duel:v1:end:{duel_id}:{round_no}`
- [ ] **Handler:** Реализовать 6 проверок + concurrency check
- [ ] **Timer:** Добавить проверку `if duel.status == "finished"` перед отправкой сообщения
- [ ] **Логирование:** Добавить structured logging для callback
- [ ] **Миграция:** Удалить/депрекейтить старый `end_round` callback
- [ ] **Тесты:** Покрыть race condition сценарии (таймер vs callback)

### UX DoD (из анализа UX)

- [ ] 🏁 Завершить раунд удалена из ReplyKeyboardMarkup
- [ ] В раунде 1 inline-кнопка есть на стартовом и AI-сообщениях
- [ ] В раунде 2 кнопка заменяется на 🏁 Завершить поединок
- [ ] Callback содержит контекст duel_id + round_no
- [ ] Старые кнопки не завершают новый state
- [ ] Повторное нажатие не ломает flow
- [ ] При active voice processing кнопка корректно блокируется
- [ ] После успешного завершения markup убирается
- [ ] Пользователь всегда видит понятный следующий шаг

---

## 🚀 План реализации

### Этап 1: Подготовка (30 мин)
1. Обновить Duel.status на новые состояния
2. Добавить `get_duel_lock()` в DuelService
3. Обновить `_process_end_round()` для использования lock

### Этап 2: Callback handler (45 мин)
1. Создать новый handler `handle_end_duel_callback`
2. Реализовать 6 проверок + concurrency
3. Удалить старый `end_round` callback

### Этап 3: Inline-кнопки (30 мин)
1. Создать `build_in_duel_keyboard()` в keyboards
2. Добавить кнопку в `_start_duel()`
3. Добавить кнопку в `_run_turn()`

### Этап 4: Таймер (15 мин)
1. Добавить проверку `if duel.status == "finished"` в `_run_timeout()`

### Этап 5: Тестирование (45 мин)
1. Тесты на race condition (таймер vs callback)
2. Тесты на старые кнопки
3. Тесты на double-click
4. Тесты на STT processing

**Итого:** ~2.5 часа

---

**READY_FOR_DEV: yes**
