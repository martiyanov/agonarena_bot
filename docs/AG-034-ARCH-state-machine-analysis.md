# AG-034-ARCH: Полный анализ графа состояний и переходов бота

## Дата анализа: 2026-03-31
## Исполнитель: Subagent AG-034-ARCH

---

## 1. ИСХОДНАЯ СХЕМА СОСТОЯНИЙ

### 1.1 Состояния базы данных (Duel.status)
```
draft                    → Начальное состояние при создании
round_1_active           → Раунд 1 активен
round_1_processing       → Обработка хода в раунде 1
round_1_transition       → Переход от раунда 1 к раунду 2
round_2_active           → Раунд 2 активен
round_2_processing       → Обработка хода в раунде 2
round_2_transition       → Переход к завершению
finished                 → Поединок завершён
cancelled                → Поединок отменён
```

### 1.2 Состояния DuelRound.status
```
pending      → Раунд создан, но не начат
in_progress  → Раунд активен
finished     → Раунд завершён
```

### 1.3 Runtime-состояния (в памяти)
```
PENDING_CUSTOM_SCENARIO_USERS: Set[int]    → Ожидание описания сценария
ACTION_IN_PROGRESS_USERS: Set[int]        → Блокировка повторных действий
FEEDBACK_REQUEST_USERS: Set[int]          → Ожидание текста обратной связи
_duel_locks: Dict[int, asyncio.Lock]      → Блокировки на уровне duel_id
```

---

## 2. ПОЛНЫЙ ГРАФ ПЕРЕХОДОВ

### 2.1 Диаграмма состояний

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              СОСТОЯНИЯ БОТА                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │   IDLE   │◄──────────────────────────────────────────┐
    │ (нет     │                                           │
    │ активного│                                           │
    │ поединка)│                                           │
    └────┬─────┘                                           │
         │                                                 │
         │ /start                                          │
         │ Выбор сценария                                  │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │      DUEL_ROUND_1_ACTIVE             │               │
    │  (status: round_1_active)            │               │
    │  (round.status: pending→in_progress) │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Ход пользователя (текст/голос)                  │
         │ ─────────────────────────────────────           │
         │ Guard: duel.status == round_1_active            │
         │       round.status == in_progress               │
         │ Action: add_message, generate AI reply          │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │   (остаёмся в DUEL_ROUND_1_ACTIVE)   │               │
    │  [цикл ходов]                        │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Кнопка "Завершить раунд"                        │
         │ ─────────────────────────────────────           │
         │ Guard: round_1.status == in_progress            │
         │       round_2.status == pending                 │
         │ Action: complete_round(round_1)                 │
         │         duel.status = round_1_transition        │
         │         duel.current_round_number = 2           │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │   DUEL_ROUND_1_FINISHED              │               │
    │  (status: round_1_transition)        │               │
    │  [временное состояние]               │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Автоматический переход                          │
         │ ─────────────────────────────────────           │
         │ Action: round_2.status = in_progress            │
         │         duel.status = round_2_active            │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │      DUEL_ROUND_2_ACTIVE             │               │
    │  (status: round_2_active)            │               │
    │  (round.status: in_progress)         │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Ход пользователя (текст/голос)                  │
         │ ─────────────────────────────────────           │
         │ Guard: duel.status == round_2_active            │
         │ Action: add_message, generate AI reply          │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │   (остаёмся в DUEL_ROUND_2_ACTIVE)   │               │
    │  [цикл ходов]                        │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Кнопка "Завершить раунд"                        │
         │ ─────────────────────────────────────           │
         │ Guard: round_2.status == in_progress            │
         │ Action: complete_round(round_2)                 │
         │         duel.status = round_2_transition        │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │      DUEL_FINISHED                   │               │
    │  (status: round_2_transition)        │               │
    │  [временное состояние]               │               │
    └────┬─────────────────────────────────┘               │
         │                                                 │
         │ Автоматический вызов судей                      │
         │ ─────────────────────────────────────           │
         │ Action: run_all_judges()                        │
         │         save_verdicts()                         │
         │         finish_duel()                           │
         │         duel.status = finished                  │
         │ ─────────────────────────────────────           │
         ▼                                                 │
    ┌──────────────────────────────────────┐               │
    │   DUEL_VERDICT_READY                 │               │
    │  (status: finished)                  │───────────────┘
    │  final_verdict != null               │ /start
    └──────────────────────────────────────┘
```

---

## 3. АНАЛИЗ НЕБЕЗОПАСНЫХ ПЕРЕХОДОВ

### 3.1 🔴 КРИТИЧЕСКИЕ: Небезопасные переходы

#### 3.1.1 Параллельное создание дуэлей (Race Condition)
```python
# Проблема в _start_duel():
existing_duel = await duel_service.get_latest_duel_for_user(...)
if existing_duel and existing_duel.status not in ("finished", "cancelled"):
    # ... показываем диалог сброса
    return

# МЕЖДУ ПРОВЕРКОЙ И СОЗДАНИЕМ - ОКНО УЯЗВИМОСТИ!
duel = await duel_service.create_duel(...)  # ← Может создать второй duel!
```

**Угроза:** Пользователь быстро дважды нажимает кнопку сценария → создаётся 2 duel'а.

**Guard Condition:**
```python
# Нужна атомарная проверка+создание ИЛИ distributed lock
async with cls.get_duel_lock(f"user:{user_id}"):
    existing = await get_latest_active_duel_for_user(...)
    if existing:
        return existing
    return await create_duel(...)
```

#### 3.1.2 Параллельное завершение раунда
```python
# В _process_end_round():
if duel.current_round_number == 1 and round_2.status == "pending":
    if round_1.status != "finished":
        await duel_service.complete_round(duel, round_1)  # ← Нет блокировки!
    await session.commit()
```

**Угроза:** Двойное нажатие "Завершить раунд" → двойной переход к раунду 2.

**Текущая защита:** `ACTION_IN_PROGRESS_USERS` — но это НЕ надёжно:
- Не переживаёт рестарт бота
- Не работает в multi-instance setup
- Нет TTL

#### 3.1.3 Параллельные ходы (Turn Collision)
```python
# В _run_turn():
await duel_service.ensure_round_started(duel, round_obj)
await session.commit()  # ← Нет блокировки на уровне duel!

# Два параллельных хода могут:
# 1. Оба пройти проверку времени
# 2. Оба добавить сообщения
# 3. Оба сгенерировать ответы AI
```

**Угроза:** Дублирование ходов, неконсистентное состояние.

**Текущая защита:** `_duel_locks` — но используется НЕПРАВИЛЬНО:
```python
# В DuelService есть _duel_locks, но в handlers они НЕ ИСПОЛЬЗУЮТСЯ!
# Нужно:
async with await DuelService.get_duel_lock(duel.id):
    # ... весь код хода
```

### 3.2 🟡 ВЫСОКИЙ: Потенциальные проблемы

#### 3.2.1 Voice Message Race Condition
```python
# В process_voice_turn():
duel, has_active_duel = await _get_active_duel_with_retry(message.from_user.id)
# Retry 3 раза с задержкой 0.1s
```

**Проблема:** 
- После создания duel может быть задержка перед commit
- Retry помогает, но не гарантирует консистентность
- Нет exponential backoff

**Улучшенный Guard:**
```python
async def _get_active_duel_with_retry(
    telegram_user_id: int, 
    max_retries: int = 5, 
    delay_sec: float = 0.1,
    max_delay: float = 2.0
) -> tuple:
    for attempt in range(max_retries):
        duel = await get_latest_duel_for_user(...)
        if duel and duel.status not in ("finished", "cancelled"):
            return duel, True
        # Exponential backoff with jitter
        delay = min(delay_sec * (2 ** attempt), max_delay)
        delay += random.uniform(0, 0.1)  # Jitter
        await asyncio.sleep(delay)
    return None, False
```

#### 3.2.2 Несоответствие состояний duel и round
```python
# Возможные неконсистентные состояния:
duel.status = "round_1_active"
round_1.status = "finished"  # ← Противоречие!

# ИЛИ

duel.current_round_number = 2
duel.status = "round_1_active"  # ← Противоречие!
round_2.status = "pending"
```

**Guard Condition:**
```python
async def validate_duel_state(duel: Duel, rounds: List[DuelRound]) -> bool:
    """Проверка консистентности состояния."""
    round_map = {r.round_number: r for r in rounds}
    
    if duel.status == "round_1_active":
        return (round_map[1].status == "in_progress" and 
                round_map[2].status == "pending")
    
    elif duel.status == "round_2_active":
        return (round_map[1].status == "finished" and 
                round_map[2].status == "in_progress" and
                duel.current_round_number == 2)
    
    # ... и т.д.
```

---

## 4. RACE CONDITIONS

### 4.1 Полный список Race Conditions

| # | Сценарий | Вероятность | Влияние | Статус защиты |
|---|----------|-------------|---------|---------------|
| 1 | Двойное создание duel | Средняя | Высокое | ❌ Нет |
| 2 | Двойное завершение раунда | Высокая | Среднее | ⚠️ Частично (in-memory) |
| 3 | Параллельные ходы | Средняя | Среднее | ❌ Нет |
| 4 | Ход после истечения времени | Средняя | Низкое | ⚠️ Проверка есть, но race possible |
| 5 | Завершение duel во время хода | Низкая | Высокое | ❌ Нет |
| 6 | Сброс duel во время обработки | Средняя | Среднее | ❌ Нет |
| 7 | Voice message после создания duel | Высокая | Низкое | ⚠️ Retry есть, но не идеально |

### 4.2 Детальный разбор Race Condition #1: Двойное создание

```
Timeline:

Поток A                    Поток B
─────────────────────────────────────────────────
get_latest_duel() → None
                           get_latest_duel() → None
                           create_duel() → duel #2
                           commit()
create_duel() → duel #1
commit()

Результат: 2 активных duel'а для одного пользователя!
```

**Решение:**
```python
async def create_duel_atomic(
    session: AsyncSession, 
    telegram_user_id: int, 
    scenario: Scenario
) -> Duel | None:
    """Атомарное создание duel с проверкой."""
    
    # 1. Блокировка на уровне пользователя
    async with await DuelService.get_user_lock(telegram_user_id):
        # 2. Проверка внутри блокировки
        existing = await get_latest_active_duel_for_user(
            session, telegram_user_id
        )
        if existing:
            return None  # Уже есть активный duel
        
        # 3. Создание
        return await create_duel(session, telegram_user_id, scenario)
```

### 4.3 Детальный разбор Race Condition #5: Завершение во время хода

```
Timeline:

Поток A (ход)              Поток B (завершение)
─────────────────────────────────────────────────
get_duel() → active
                           get_duel() → active
                           complete_round()
                           finish_duel()
                           commit()
add_message()  # ← Добавляет в finished duel!
generate_reply()
commit()

Результат: Сообщения в завершённом duel!
```

**Решение:**
```python
async def _run_turn(...):
    async with await DuelService.get_duel_lock(duel.id):
        # Перечитываем состояние внутри блокировки
        duel = await duel_service.get_duel(session, duel.id)
        if duel.status != "round_1_active" and duel.status != "round_2_active":
            raise DuelNotActiveError("Duel is not active")
        # ... продолжаем ход
```

---

## 5. DEADLOCK АНАЛИЗ

### 5.1 Потенциальные Deadlock

#### 5.1.1 Deadlock в _duel_locks
```python
# Текущая реализация:
_duel_locks: dict[int, asyncio.Lock] = {}

@classmethod
async def get_duel_lock(cls, duel_id: int) -> asyncio.Lock:
    if duel_id not in cls._duel_locks:
        cls._duel_locks[duel_id] = asyncio.Lock()
    return cls._duel_locks[duel_id]
```

**Проблема:** 
- Нет cleanup при ошибках
- Словарь растёт бесконечно
- При high load → memory leak

**Решение:**
```python
import weakref
from contextlib import asynccontextmanager

class DuelLockManager:
    _locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()
    _lock_creation_lock = asyncio.Lock()
    
    @classmethod
    @asynccontextmanager
    async def acquire(cls, duel_id: int, timeout: float = 30.0):
        async with cls._lock_creation_lock:
            if duel_id not in cls._locks:
                cls._locks[duel_id] = asyncio.Lock()
            lock = cls._locks[duel_id]
        
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            yield
        finally:
            lock.release()
```

#### 5.1.2 Deadlock базы данных
```python
# В _finish_duel_from_menu():
contexts = judge_service.build_contexts_for_duel(...)
verdicts = await judge_service.run_all_judges(contexts)  # ← Внешние вызовы!
for verdict in verdicts:
    session.add(await judge_service.save_verdict(duel, verdict))
```

**Проблема:** 
- `run_all_judges` делает HTTP запросы к LLM
- Транзакция открыта всё это время
- При долгом ответе LLM → connection pool exhaustion

**Решение:**
```python
async def _finish_duel_from_menu(...):
    # 1. Собираем данные
    async with db_session.AsyncSessionLocal() as session:
        duel = await get_duel(...)
        messages = await get_messages(...)
    
    # 2. Вызываем LLM вне транзакции
    verdicts = await judge_service.run_all_judges(contexts)
    
    # 3. Сохраняем результаты
    async with db_session.AsyncSessionLocal() as session:
        async with session.begin():
            for verdict in verdicts:
                session.add(await judge_service.save_verdict(duel, verdict))
            await finish_duel(duel, final_verdict)
```

---

## 6. ПРЕРЫВАНИЕ ПОЛЬЗОВАТЕЛЕМ

### 6.1 Сценарии прерывания

| Сценарий | Текущее поведение | Проблема | Рекомендация |
|----------|-------------------|----------|--------------|
| /start во время duel | Показывает меню с опцией продолжить | ✅ Корректно | Добавить явную кнопку "Сдаться" |
| Новый сценарий во время duel | Предлагает сбросить текущий | ✅ Корректно | Добавить подтверждение |
| Выход из чата | Duel остаётся активным | ⚠️ Зомби-duel | Добавить TTL + cleanup job |
| Отключение бота | Состояние в БД | ✅ Сохраняется | Нужна recovery логика при старте |
| Двойное нажатие кнопки | Зависит от кнопки | ❌ Не всегда защищено | Унифицировать защиту |

### 6.2 Обработка прерываний по состояниям

```
┌────────────────────────────────────────────────────────────────┐
│                    ОБРАБОТКА ПРЕРЫВАНИЙ                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  IDLE                                                          │
│  ├── /start → Показать меню (OK)                              │
│  └── Любое сообщение → Подсказка выбрать сценарий (OK)        │
│                                                                │
│  DUEL_ROUND_1_ACTIVE                                           │
│  ├── /start → Меню с опцией "Продолжить" (OK)                 │
│  ├── Новый сценарий → Диалог сброса (OK)                      │
│  ├── "Завершить раунд" → Переход к раунду 2 (OK)              │
│  └── Таймаут → Автозавершение? (НЕ РЕАЛИЗОВАНО)               │
│                                                                │
│  DUEL_ROUND_2_ACTIVE                                           │
│  ├── /start → Меню с опцией "Продолжить" (OK)                 │
│  ├── Новый сценарий → Диалог сброса (OK)                      │
│  ├── "Завершить раунд" → Завершение duel (OK)                 │
│  └── Таймаут → Автозавершение? (НЕ РЕАЛИЗОВАНО)               │
│                                                                │
│  DUEL_FINISHED / DUEL_VERDICT_READY                            │
│  ├── /start → Меню (OK)                                       │
│  └── Новый сценарий → Новый duel (OK)                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. GUARD CONDITIONS (ПОЛНЫЙ СПИСОК)

### 7.1 Guard для каждого перехода

```python
# ============================================
# TRANSITION: /start → IDLE
# ============================================
GUARD: True  # Всегда разрешено
ACTION: show_main_menu()

# ============================================
# TRANSITION: Выбор сценария → DUEL_ROUND_1_ACTIVE
# ============================================
GUARD: 
    - user_id not in PENDING_CUSTOM_SCENARIO_USERS
    - Нет активного duel (или пользователь подтвердил сброс)
    - scenario.is_active == True
ACTION: 
    - create_duel()
    - create round_1, round_2
    - duel.status = "round_1_active"

# ============================================
# TRANSITION: Ход в раунде → DUEL_ROUND_1_ACTIVE (остаёмся)
# ============================================
GUARD:
    - duel.status IN ("round_1_active", "round_2_active")
    - round.status == "in_progress"
    - NOT is_round_expired(duel, round)
    - message.content not empty
    - user_id not in ACTION_IN_PROGRESS_USERS
LOCK: duel_id
ACTION:
    - add_message(user)
    - generate_ai_reply()
    - add_message(ai)

# ============================================
# TRANSITION: Завершить раунд 1 → DUEL_ROUND_1_FINISHED
# ============================================
GUARD:
    - duel.status == "round_1_active"
    - round_1.status == "in_progress"
    - round_2.status == "pending"
    - user_id not in ACTION_IN_PROGRESS_USERS
LOCK: duel_id
ACTION:
    - round_1.status = "finished"
    - round_1.finished_at = now()
    - duel.status = "round_1_transition"
    - duel.current_round_number = 2

# ============================================
# TRANSITION: DUEL_ROUND_1_FINISHED → DUEL_ROUND_2_ACTIVE
# ============================================
GUARD:
    - duel.status == "round_1_transition"
    - round_1.status == "finished"
    - round_2.status == "pending"
ACTION:
    - round_2.status = "in_progress"
    - round_2.started_at = now()
    - duel.status = "round_2_active"

# ============================================
# TRANSITION: Ход в раунде 2 → DUEL_ROUND_2_ACTIVE (остаёмся)
# ============================================
GUARD: [аналогично раунду 1]

# ============================================
# TRANSITION: Завершить раунд 2 → DUEL_FINISHED
# ============================================
GUARD:
    - duel.status == "round_2_active"
    - round_2.status == "in_progress"
    - user_id not in ACTION_IN_PROGRESS_USERS
LOCK: duel_id
ACTION:
    - round_2.status = "finished"
    - round_2.finished_at = now()
    - duel.status = "round_2_transition"

# ============================================
# TRANSITION: DUEL_FINISHED → DUEL_VERDICT_READY
# ============================================
GUARD:
    - duel.status == "round_2_transition"
    - round_1.status == "finished"
    - round_2.status == "finished"
ACTION:
    - run_all_judges()
    - save_verdicts()
    - duel.status = "finished"
    - duel.final_verdict = summary
    - cleanup_duel_lock(duel.id)

# ============================================
# TRANSITION: Голосовое сообщение → зависит от состояния
# ============================================
GUARD:
    - transcription_service.is_configured()
    - file_size < MAX_SIZE
ACTION:
    - transcribe()
    - route_to_appropriate_handler()  # Как текстовое сообщение
```

---

## 8. РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ

### 8.1 Критические (P0) — Нужно сделать немедленно

1. **Добавить distributed lock на duel_id для всех операций**
   ```python
   # В каждом handler, который меняет duel:
   async with await DuelLockManager.acquire(duel.id, timeout=30.0):
       # ... операции
   ```

2. **Атомарное создание duel**
   ```python
   # Добавить UNIQUE constraint в БД:
   # ALTER TABLE duels ADD CONSTRAINT unique_active_duel_per_user 
   #   UNIQUE (user_telegram_id) WHERE status NOT IN ('finished', 'cancelled');
   ```

3. **Улучшить ACTION_IN_PROGRESS_USERS**
   ```python
   # Добавить TTL + Redis/memcached для multi-instance
   class ActionLock:
       def __init__(self, redis_client):
           self.redis = redis_client
           self.ttl = 30  # seconds
       
       async def acquire(self, user_id: int) -> bool:
           key = f"action_lock:{user_id}"
           return await self.redis.set(key, "1", nx=True, ex=self.ttl)
   ```

### 8.2 Высокий приоритет (P1)

4. **Добавить state validation layer**
   ```python
   class DuelStateValidator:
       @staticmethod
       def validate_transition(
           from_status: str, 
           to_status: str, 
           context: dict
       ) -> bool:
           valid_transitions = {
               "draft": ["round_1_active"],
               "round_1_active": ["round_1_processing", "round_1_transition"],
               "round_1_processing": ["round_1_active"],
               "round_1_transition": ["round_2_active"],
               "round_2_active": ["round_2_processing", "round_2_transition"],
               "round_2_processing": ["round_2_active"],
               "round_2_transition": ["finished"],
               "finished": [],
               "cancelled": [],
           }
           return to_status in valid_transitions.get(from_status, [])
   ```

5. **Добавить cleanup job для зомби-duel'ов**
   ```python
   # Cron job каждые 24 часа
   async def cleanup_stale_duels():
       stale_threshold = datetime.utcnow() - timedelta(hours=24)
       await session.execute(
           update(Duel)
           .where(
               Duel.status.not_in(["finished", "cancelled"]),
               Duel.updated_at < stale_threshold
           )
           .values(status="cancelled")
       )
   ```

6. **Улучшить обработку ошибок в голосовых сообщениях**
   ```python
   # Добавить circuit breaker для STT
   from circuitbreaker import circuit
   
   @circuit(failure_threshold=5, recovery_timeout=60)
   async def transcribe_with_circuit_breaker(audio_path: Path) -> str:
       return await transcription_service.transcribe(audio_path)
   ```

### 8.3 Средний приоритет (P2)

7. **Добавить observability**
   ```python
   # Метрики для каждого перехода
   from prometheus_client import Counter, Histogram
   
   transition_counter = Counter(
       'duel_transitions_total',
       'Total duel state transitions',
       ['from_state', 'to_state', 'result']
   )
   
   transition_duration = Histogram(
       'duel_transition_duration_seconds',
       'Time spent in transition',
       ['transition_name']
   )
   ```

8. **Добавить idempotency keys**
   ```python
   # Для защиты от дублирования при retry
   async def process_turn(
       message: Message,
       idempotency_key: str | None = None
   ):
       if idempotency_key:
           cached = await cache.get(f"turn:{idempotency_key}")
           if cached:
               return cached  # Возвращаем кэшированный результат
   ```

### 8.4 Низкий приоритет (P3)

9. **Добавить soft delete для duel'ов**
10. **Добавить аудит-лог всех переходов**
11. **Реализовать graceful shutdown с завершением активных операций**

---

## 9. ИТОГОВАЯ ТАБЛИЦА РИСКОВ

| Риск | Вероятность | Влияние | Статус | Приоритет |
|------|-------------|---------|--------|-----------|
| Двойное создание duel | Средняя | Высокое | ❌ Нет защиты | P0 |
| Двойное завершение раунда | Высокая | Среднее | ⚠️ Частично | P0 |
| Параллельные ходы | Средняя | Среднее | ❌ Нет защиты | P0 |
| Неконсистентные состояния | Низкая | Высокое | ❌ Нет валидации | P1 |
| Зомби-duel'ы | Высокая | Низкое | ❌ Нет cleanup | P1 |
| Утечка памяти в _duel_locks | Средняя | Среднее | ⚠️ Частично | P1 |
| Deadlock БД при judging | Низкая | Высокое | ⚠️ Возможен | P1 |
| Race condition в voice | Высокая | Низкое | ⚠️ Retry есть | P2 |

---

## 10. РЕКОМЕНДУЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ДЕЙСТВИЙ

```
Немедленно (сегодня):
├── 1. Добавить DuelLockManager с timeout
├── 2. Обновить все handlers для использования блокировок
└── 3. Добавить UNIQUE constraint на активные duel'ы

На этой неделе:
├── 4. Реализовать ActionLock с Redis/TTL
├── 5. Добавить state validation layer
└── 6. Написать тесты на race conditions

На следующей неделе:
├── 7. Добавить cleanup job для зомби-duel'ов
├── 8. Улучшить observability
└── 9. Добавить circuit breaker для внешних вызовов
```

---

**Конец анализа AG-034-ARCH**
