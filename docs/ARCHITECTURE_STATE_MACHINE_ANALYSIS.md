# AG-032-ARCH: Полный анализ графа состояний и переходов бота Agon Arena

## 📊 Схема состояний (State Machine)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ПОЛНАЯ СХЕМА СОСТОЯНИЙ                                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │   /start    │
    └──────┬──────┘
           │
           ▼
┌──────────────────────┐
│       IDLE           │◄────────────────────────────────────────┐
│ (нет активного duel) │                                         │
│ duel.status = N/A    │                                         │
└──────────┬───────────┘                                         │
           │                                                      │
           │  Выбор сценария                                      │
           │  (pick_scenario:{id} или random)                     │
           ▼                                                      │
┌──────────────────────┐                                          │
│  DUEL_ROUND_1_ACTIVE │                                          │
│ duel.status =        │                                          │
│ "round_1_active"     │                                          │
│ round.status =       │                                          │
│ "in_progress"        │                                          │
└──────────┬───────────┘                                          │
           │                                                      │
           │  Ход пользователя (текст/голос)                      │
           │  _run_turn()                                         │
           ├──────────────────────────────────────────────────────┤
           │                                                      │
           │  🏁 Завершить раунд                                  │
           │  _process_end_round()                                │
           ▼                                                      │
┌──────────────────────┐                                          │
│ DUEL_ROUND_1_FINISHED│                                          │
│ duel.status =        │                                          │
│ "round_1_transition" │                                          │
│ round1.status =      │                                          │
│ "finished"           │                                          │
└──────────┬───────────┘                                          │
           │                                                      │
           │  Автоматический переход                              │
           │  (в рамках _process_end_round)                       │
           ▼                                                      │
┌──────────────────────┐                                          │
│  DUEL_ROUND_2_ACTIVE │                                          │
│ duel.status =        │                                          │
│ "round_2_active"     │                                          │
│ round2.status =      │                                          │
│ "in_progress"        │                                          │
└──────────┬───────────┘                                          │
           │                                                      │
           │  Ход пользователя (текст/голос)                      │
           │  _run_turn()                                         │
           ├──────────────────────────────────────────────────────┤
           │                                                      │
           │  🏁 Завершить поединок                               │
           │  _process_end_round()                                │
           ▼                                                      │
┌──────────────────────┐                                          │
│    DUEL_FINISHED     │                                          │
│ duel.status =        │                                          │
│ "round_2_transition" │                                          │
│ round2.status =      │                                          │
│ "finished"           │                                          │
└──────────┬───────────┘                                          │
           │                                                      │
           │  _finish_duel_from_menu()                            │
           │  (вызов судей)                                       │
           ▼                                                      │
┌──────────────────────┐                                          │
│ DUEL_VERDICT_READY   │                                          │
│ duel.status =        │                                          │
│ "finished"           │                                          │
│ final_verdict != null│                                          │
└──────────┬───────────┘                                          │
           │                                                      │
           │  /start или новый поединок                           │
           └──────────────────────────────────────────────────────┘
```

---

## 🔴 НЕБЕЗОПАСНЫЕ ПЕРЕХОДЫ (Critical Issues)

### 1. **Race Condition при создании duel**
**Место:** `menu.py:_start_duel()` - строки 155-195

```python
# Проблема: проверка и создание не атомарны
existing_duel = await duel_service.get_latest_duel_for_user(...)  # SELECT
if existing_duel and existing_duel.status not in ("finished", "cancelled"):
    # ... показываем диалог ...
    return
# ... создаём новый duel ...  # INSERT
```

**Сценарий race condition:**
1. Пользователь быстро дважды кликает кнопку сценария
2. Два запроса одновременно проходят проверку `existing_duel`
3. Создаются ДВА активных duel для одного пользователя

**Уровень риска:** 🔴 CRITICAL

### 2. **Race Condition при завершении раунда**
**Место:** `menu.py:_process_end_round()` - строки 850-900

```python
# Проблема: проверка статуса и изменение не защищены
if duel.current_round_number == 1 and round_2.status == "pending":
    if round_1.status != "finished":
        await duel_service.complete_round(duel, round_1)  # Может вызваться 2 раза!
    await session.commit()
```

**Сценарий:**
1. Пользователь дважды нажимает "Завершить раунд"
2. Оба запроса проходят проверку `round_1.status != "finished"`
3. `complete_round()` вызывается дважды → data corruption

**Уровень риска:** 🔴 CRITICAL

### 3. **Небезопасный переход: голосовое без активного duel**
**Место:** `menu.py:process_voice_turn()` - строки 1000-1050

```python
# Проблема: проверка PENDING_CUSTOM_SCENARIO_USERS после проверки duel
duel, has_active_duel = await _get_active_duel_with_retry(...)
if has_active_duel:
    await _run_turn(...)  # OK
    return

# Эта проверка может пропустить голосовое в неправильный контекст
if message.from_user.id in PENDING_CUSTOM_SCENARIO_USERS:
    await _start_custom_duel(...)  # Риск: пользователь уже начал другой duel
```

**Уровень риска:** 🟡 MEDIUM

### 4. **Небезопасный переход: timer vs user action**
**Место:** `round_timer_service.py:_run_timeout()`

```python
# Проблема: проверка статуса и действие разделены sleep
await asyncio.sleep(delay_seconds)
# ... проверки ...
await duel_service.complete_round(duel, round_obj)  # Может конфликтовать с user action
```

**Сценарий:**
1. Timer запущен на 120 секунд
2. Пользователь нажимает "Завершить раунд" на 119-й секунде
3. Timer просыпается и тоже пытается завершить раунд

**Уровень риска:** 🟠 HIGH

---

## 🔄 RACE CONDITIONS (Полный список)

| # | Место | Условие | Последствие | Уровень |
|---|-------|---------|-------------|---------|
| 1 | `_start_duel()` | Двойной клик по сценарию | 2+ активных duel | 🔴 CRITICAL |
| 2 | `_process_end_round()` | Двойной клик "Завершить" | Повторное завершение | 🔴 CRITICAL |
| 3 | `_run_turn()` | Ход + истечение таймера | Несогласованное состояние | 🟠 HIGH |
| 4 | `RoundTimerService.schedule()` | Новый таймер до отмены старого | Утечка задач | 🟡 MEDIUM |
| 5 | `ACTION_IN_PROGRESS_USERS` | Не атомарная проверка | Обход защиты | 🟡 MEDIUM |
| 6 | `PENDING_CUSTOM_SCENARIO_USERS` | Многопоточный доступ | Несогласованность | 🟡 MEDIUM |
| 7 | `_finish_duel_from_menu()` | Двойной вызов завершения | Дублирование вердиктов | 🟠 HIGH |

---

## 🔒 DEADLOCK ВОЗМОЖЕНОСТИ

### 1. **Duel Lock Cleanup**
**Место:** `duel_service.py`

```python
_duel_locks: dict[int, asyncio.Lock] = {}

# Проблема: lock создаётся, но не всегда очищается
def cleanup_duel_lock(cls, duel_id: int) -> None:
    cls._duel_locks.pop(duel_id, None)  # Только при finish_duel!
```

**Сценарий deadlock:**
1. Duel создан, lock создан
2. Duel не завершён корректно (ошибка, сброс)
3. Lock остаётся в памяти навсегда
4. При перезапуске бота словарь очищается → OK
5. Но при длительной работе → утечка памяти

**Риск:** 🟡 MEDIUM (только утечка памяти, не deadlock)

### 2. **Database Transaction Deadlock**
**Место:** Все async with session

```python
# Проблема: долгие транзакции
async with db_session.AsyncSessionLocal() as session:
    # ... много операций ...
    await opponent_service.generate_reply(context)  # LLM вызов внутри транзакции!
    # ... ещё операции ...
    await session.commit()
```

**Риск:** 🟡 MEDIUM (SQLite не поддерживает настоящий deadlock, но есть timeout)

---

## ⛔ ПРЕРЫВАНИЕ ПОЛЬЗОВАТЕЛЕМ

### Сценарии прерывания:

| Действие пользователя | Текущее поведение | Проблема |
|----------------------|-------------------|----------|
| /start во время duel | Показывает меню с опциями | ✅ OK |
| Выбор нового сценария при активном duel | Диалог подтверждения | ✅ OK |
| Отправка голосового без контекста | "Нет активного поединка" | ✅ OK |
| Двойной клик кнопки | Race condition | 🔴 CRITICAL |
| Закрытие чата во время duel | Duel остаётся активным | 🟡 MEDIUM |
| /start после долгого перерыва | Duel всё ещё активен | 🟡 MEDIUM |

### Отсутствующие guard conditions:

```python
# Нужно добавить:

# 1. Проверка expired duel при /start
async def check_expired_duels(user_id):
    duel = await get_latest_duel(user_id)
    if duel and is_expired(duel):
        duel.status = "expired"
        await notify_user("Ваш поединок истёк по времени")

# 2. Проверка concurrent actions
async def with_action_lock(user_id, action):
    if user_id in ACTION_IN_PROGRESS_USERS:
        raise ConcurrentActionError()
    ACTION_IN_PROGRESS_USERS.add(user_id)
    try:
        return await action()
    finally:
        ACTION_IN_PROGRESS_USERS.discard(user_id)
```

---

## 🛡️ GUARD CONDITIONS (Рекомендуемые)

### Для каждого перехода:

```
┌────────────────────────────────────────────────────────────────┐
│                    GUARD CONDITIONS MAP                        │
└────────────────────────────────────────────────────────────────┘

IDLE → DUEL_ROUND_1_ACTIVE:
  ✓ Пользователь не имеет active duel
  ✓ Сценарий существует и is_active=True
  ✓ Нет pending custom scenario для этого user
  ✓ Нет concurrent action

DUEL_ROUND_1_ACTIVE → DUEL_ROUND_1_ACTIVE (ход):
  ✓ Duel существует и status == "round_1_active"
  ✓ Round 1 status == "in_progress"
  ✓ Время не истекло
  ✓ Нет concurrent action для этого duel

DUEL_ROUND_1_ACTIVE → DUEL_ROUND_1_FINISHED:
  ✓ Duel status == "round_1_active"
  ✓ Round 1 status == "in_progress"
  ✓ Round 2 status == "pending"
  ✓ Нет concurrent complete_round

DUEL_ROUND_1_FINISHED → DUEL_ROUND_2_ACTIVE:
  ✓ Round 1 status == "finished"
  ✓ Round 2 status == "pending"
  ✓ Duel current_round_number == 2

DUEL_ROUND_2_ACTIVE → DUEL_ROUND_2_ACTIVE (ход):
  ✓ Duel status == "round_2_active"
  ✓ Round 2 status == "in_progress"
  ✓ Время не истекло

DUEL_ROUND_2_ACTIVE → DUEL_FINISHED:
  ✓ Duel status == "round_2_active"
  ✓ Round 2 status == "in_progress"
  ✓ Round 1 status == "finished"
  ✓ Нет concurrent complete_round

DUEL_FINISHED → DUEL_VERDICT_READY:
  ✓ Round 1 status == "finished"
  ✓ Round 2 status == "finished"
  ✓ Duel status != "finished" (предотвратить повтор)
  ✓ Нет concurrent judging

DUEL_VERDICT_READY → IDLE:
  ✓ Duel status == "finished"
  ✓ final_verdict is not null
```

---

## 📋 РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ

### Priority 1 (Critical - Fix Immediately):

1. **Добавить duel-level locking:**
```python
async def with_duel_lock(duel_id: int, coro):
    lock = DuelService.get_duel_lock(duel_id)
    async with lock:
        return await coro
```

2. **Атомарная проверка при создании duel:**
```python
# Использовать SELECT FOR UPDATE или unique constraint
# Или: проверка + создание в одной транзакции с повторной проверкой
```

3. **Idempotent operations:**
```python
async def complete_round(self, duel, round_obj):
    # Проверить ещё раз внутри lock
    if round_obj.status == "finished":
        return  # Already done
    # ... proceed
```

### Priority 2 (High):

4. **Timer synchronization:**
```python
# Перед действием пользователя - отменить таймер
round_timer_service.cancel(duel_id, round_number)
# Затем выполнить действие
```

5. **Session scope minimization:**
```python
# НЕ делать LLM вызовы внутри транзакции
# Сначала собрать данные, закрыть session, потом LLM
```

### Priority 3 (Medium):

6. **Expired duel cleanup:**
```python
# Периодическая задача или проверка при /start
if duel.created_at < now - timedelta(hours=24):
    duel.status = "expired"
```

7. **Memory cleanup:**
```python
# Очистка ACTION_IN_PROGRESS_USERS по таймауту
# Очистка _duel_locks для finished duels
```

---

## 🔍 ДОПОЛНИТЕЛЬНЫЕ ПРОБЛЕМЫ

### 1. **Несоответствие статусов**
```python
# duel.status может быть:
# "round_1_active", "round_1_processing", "round_1_transition",
# "round_2_active", "round_2_processing", "round_2_transition",
# "finished", "judging", "cancelled"

# Но проверки часто только на "finished":
if duel.status == "finished":  # Пропускает "cancelled", "judging"!
```

### 2. **Отсутствие валидации round_number**
```python
# duel.current_round_number может быть 1 или 2
# Нет проверки на некорректные значения
```

### 3. **Необработанные исключения в таймерах**
```python
# В RoundTimerService._run_timeout нет глобального try-except
# Исключение убьёт всю задачу, lock останется
```

---

## 📊 ИТОГОВАЯ ТАБЛИЦА РИСКОВ

| Риск | Вероятность | Влияние | Статус |
|------|-------------|---------|--------|
| Двойное создание duel | Средняя | Высокое | 🔴 Открыт |
| Двойное завершение раунда | Средняя | Высокое | 🔴 Открыт |
| Timer vs User conflict | Средняя | Среднее | 🟠 Открыт |
| Утечка памяти (locks) | Низкая | Низкое | 🟡 Открыт |
| Несогласованность статусов | Низкая | Высокое | 🟡 Открыт |
| LLM в транзакции | Высокая | Среднее | 🟡 Открыт |

---

*Анализ выполнен: 2026-03-31*
*Аналитик: Agora (subagent)*
