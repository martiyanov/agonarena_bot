# Task Context — Контекст задач Agon Arena

**Дата создания:** 2026-03-29  
**Цель:** Сохранение контекста между задачами, предотвращение потерь знаний

---

## 📋 Активные задачи

### AG-017: Inline-кнопка "Завершить раунд"

**Статус:** ready_for_final_test  
**Контекст:**

**Проблема:**
- Кнопка "🏁 Завершить раунд" в нижнем меню скрывается при переписке
- Пользователь не видит кнопку в нужный момент

**Решение:**
- Перенести кнопку из ReplyKeyboardMarkup в InlineKeyboardMarkup
- Добавлять к каждому сообщению раунда
- Callback с versioning: `duel:v1:end:{duel_id}:{round_no}`

**Изменения:**
- `app/bot/handlers/menu.py` — callback handler (6 проверок), inline кнопки
- `app/bot/keyboards/main_menu.py` — `build_in_duel_keyboard()`
- `app/services/duel_service.py` — state machine (6 состояний), lock
- `app/services/round_timer_service.py` — проверка finished статуса

**Баги (исправлены):**
1. AG-017-BUG-1: Дублирование "Раунд 1:" в выводе судей ✅
2. AG-017-BUG-2: Конфликт handlers (кнопка "Сценарии") ✅

**Тесты:**
- Unit: 22/22 PASS
- Handlers: 4/4 PASS
- Manual: pending (2)

**Связанные задачи:** —  
**Влияет на:** duel_service, menu handlers, keyboards

---

## 📊 История задач

### Завершённые

| ID | Название | Статус | Баги | Уроки |
|----|----------|--------|------|-------|
| AG-017 | Inline-кнопка | ready_for_final_test | 2 (fix) | MANUAL TEST раньше, CODE_REVIEW, Bug Registry |

---

## 🔗 Пересечения задач

**Механизм проверки:**

При получении новой задачи:
1. PM читает этот файл + task-tracker.json
2. Проверяет пересечения по:
   - **Файлам:** Те же ли файлы изменяются?
   - **Функционалу:** Тот же компонент?
   - **Багам:** Связано ли с известными багами?
   - **Контексту:** Требует ли тех же знаний?

3. Если пересечение найдено → вопрос пользователю:
   ```
   ⚠️ Найдено пересечение с задачей AG-XXX
   
   Пересечение: [файлы/функционал]
   
   Варианты:
   1. Объединить задачи
   2. Приоритизировать (сначала AG-XXX)
   3. Разделить (независимая реализация)
   4. Отложить новую задачу
   ```

---

## 📝 Заметки

### Архитектура

**State Machine (Duel.status):**
```
idle → round_1_active → round_1_processing → round_1_transition
     → round_2_active → round_2_processing → round_2_transition → finished
```

**Concurrency:**
- `get_duel_lock(duel_id)` — lock per duel
- `ACTION_IN_PROGRESS_USERS` — lock per user

**Callback Flow:**
- Format: `duel:v1:end:{duel_id}:{round_no}`
- 6 проверок в handler

### Известные проблемы

**Handler Conflicts:**
- Было: SCENARIOS_BUTTON в двух handlers
- Fix: Удалить из handle_rules_button
- Prevention: test_handlers.py (проверка конфликтов)

**Judge Formatting:**
- Было: Дублирование "Раунд 1:"
- Fix: Удалить префикс в _format_final_verdict
- Prevention: Unit тест на форматирование

---

## 🎯 Backlog

**Process Improvements (внедрено 2026-03-29):**
- [x] MANUAL TEST раньше (после DEV, до TEST)
- [x] CODE_REVIEW этап перед TEST
- [x] Bug Registry
- [x] Task Context файл
- [ ] E2E тесты (Telegram Bot API)
- [ ] Реестр handlers
- [ ] CI/CD pipeline

**Задачи:**
- [ ] AG-018: E2E тесты для Telegram UI
- [ ] AG-019: Реестр handlers (какая кнопка → какой handler)
- [ ] AG-020: CI/CD pipeline (auto-test на commit)

---

**Обновлено:** 2026-03-29 (AG-017)
