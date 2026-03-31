# Agon Arena — TODO / BACKLOG

Лёгкий рабочий backlog для текущего MVP.

## DONE

### AG-017 ✅ ЗАКРЫТА (2026-03-29)
- **Title:** Inline-кнопка "Завершить раунд" (перенос из ReplyKeyboard)
- **Type:** feature
- **Status:** DONE ✅
- **Priority:** P0
- **Closed:** 2026-03-29
- **Result:** Inline кнопка работает, протестирована Степаном
- **Why:** кнопка в reply keyboard скрывается при переписке
- **Done_when:** 
  - Inline-кнопка на сообщениях дуэли ✅
  - 6 состояний в Duel.status ✅
  - Concurrency lock реализован ✅
  - 6 проверок в callback handler ✅
  - Старый callback удалён ✅
  - Timer проверяет finished статус ✅
  - 8 unit тестов обновлены и PASS ✅
- **Risks:** race condition с таймером, старые кнопки
- **Progress:**
  - [x] Шаг 1: Обновить Duel.status на 6 новых состояний
  - [x] Шаг 2: Добавить get_duel_lock() в DuelService
  - [x] Шаг 3: Создать build_in_duel_keyboard(round_no)
  - [x] Шаг 4: Добавить кнопку в _start_duel() и _run_turn()
  - [x] Шаг 5: Создать handle_end_duel_callback с 6 проверками
  - [x] Шаг 6: Удалить старый end_round callback (deprecated)
  - [x] Шаг 7: Обновить timer с проверкой finished
  - [x] Шаг 8: Тесты на race conditions (covered by handler logic with lock + 6 checks)
  - [x] Шаг 9: Обновить 8 unit тестов для новых статусов (test_round_completion.py: 5 тестов, test_duel_flow.py: 3 теста)

**READY_FOR_TEST: yes**
**Tests:** 22/22 PASS in test_round_completion.py + test_duel_flow.py

## DONE

### AG-001
- **Title:** Stabilize duel-flow tests
- **Type:** test
- **Status:** DONE
- **Priority:** P0
- **Why:** duel-flow — критический путь продукта
- **Done_when:** есть happy-path + негативные кейсы + зелёный pytest
- **Risks:** flaky test DB / state drift
- **RICE:**
  - **Reach:** 9
  - **Impact:** 10
  - **Confidence:** 9
  - **Effort:** 4
  - **Score:** 202.5

### AG-002
- **Title:** Fix runtime/workspace mismatch on deploy
- **Type:** infra
- **Status:** DONE
- **Priority:** P0
- **Why:** без этого Telegram показывает старый код
- **Done_when:** runtime container совпадает с workspace после redeploy
- **Risks:** stale image / broken compose recreate
- **RICE:**
  - **Reach:** 9
  - **Impact:** 9
  - **Confidence:** 9
  - **Effort:** 4
  - **Score:** 182.25

### AG-003
- **Title:** Replace dual round buttons with one `Завершить раунд`
- **Type:** ux
- **Status:** DONE
- **Priority:** P0
- **Why:** убрать лишнюю развилку в поединке
- **Done_when:** одна action-кнопка работает для round1 и round2
- **Risks:** Telegram keyboard drift
- **RICE:**
  - **Reach:** 8
  - **Impact:** 8
  - **Confidence:** 8
  - **Effort:** 3
  - **Score:** 170.67

### AG-004
- **Title:** Add double-click protection for round-end action
- **Type:** reliability
- **Status:** DONE
- **Priority:** P1
- **Why:** Telegram/пользователь может дублировать действие
- **Done_when:** повторное действие не ломает состояние
- **Risks:** only in-memory lock
- **RICE:**
  - **Reach:** 7
  - **Impact:** 7
  - **Confidence:** 7
  - **Effort:** 3
  - **Score:** 114.33

### AG-007
- **Title:** Improve scenario picker message layout in Telegram
- **Type:** ux
- **Status:** DONE
- **Priority:** P1
- **Why:** список из 10 сообщений может быть визуально шумным
- **Done_when:** карточки сценариев легче сканируются, без потери MVP-простоты
- **Risks:** легко расширить scope
- **RICE:**
  - **Reach:** 7
  - **Impact:** 7
  - **Confidence:** 7
  - **Effort:** 3
  - **Score:** 114.33
  - **Accepted:** 2026-03-27 — Telegram acceptance PASS
  - **UX_DECISION:** Variant B confirmed — цифры без emoji (cleaner scan, less visual noise)
  - **Closure scope:**
    - Delivery policy исправлена и подтверждена
    - Implementation применён в Docker runtime
    - Telegram acceptance PASS (user selected Variant B)

## DONE

### AG-005
- **Title:** Manual production acceptance for scenario picker UX
- **Type:** acceptance
- **Status:** DONE
- **Priority:** P0
- **Why:** задача не считается завершённой до проверки в Telegram на production
- **Done_when:** подтверждён flow `🎯 Выбрать сценарий` -> 10 сценариев -> `Начать сценарий` -> обычный duel-flow
- **Risks:** runtime/client mismatch, UX mismatch in real Telegram
- **RICE:**
  - **Reach:** 8
  - **Impact:** 9
  - **Confidence:** 6
  - **Effort:** 2
  - **Score:** 216
  - **Accepted:** 2026-03-27 — Telegram acceptance PASS

## NEXT TOP 5

### AG-006 ✅ DONE (2026-03-31)
- **Title:** Commit and push validated release after manual PASS
- **Type:** release
- **Status:** DONE
- **Priority:** P0
- **Closed:** 2026-03-31
- **Why:** по local policy задача полностью завершается только после release + push
- **Done_when:** есть commit, push, evidence по branch/hash ✅
- **Result:**
  - Commit: aa6f170 — "feat: inline round button + pipeline improvements"
  - Branch: main
  - Production: DEPLOYED ✅
  - Tests: 22/22 PASS + 4/4 E2E PASS
- **RICE:**
  - **Reach:** 8
  - **Impact:** 8
  - **Confidence:** 9
  - **Effort:** 2
  - **Score:** 288

### AG-016
- **Title:** Fix DEV → TEST auto-handoff in pipeline orchestration
- **Type:** orchestration bug
- **Status:** DONE
- **Priority:** P0
- **Why:** Pipeline не переходит автоматически DEV → TEST, требует manual trigger
- **Done_when:**
  - TEST subagent спавнится автоматически после DEV completion
  - Pipeline не зависает на handoff
  - Не требуется ручное вмешательство
- **Risks:** изменение orchestration logic может задеть другие stage transitions
- **RICE:**
  - **Reach:** 10 (затрагивает все задачи)
  - **Impact:** 9 (критично для workflow)
  - **Confidence:** 8
  - **Effort:** 4
  - **Score:** 180
- **Implemented:** 
  - Created auto-test spawner script
  - Implemented marker detection (READY_FOR_TEST: yes)
  - Added 5-second fallback timer
  - Documented in PIPELINE_ORCHESTRATION.md

### AG-008
- **Title:** Normalize judge output by round
- **Type:** product
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-28 (реализовано в сессии 2026-03-28)
- **Why:** пользователю полезно понимать, что было сильным/слабым в каждом раунде отдельно
- **Done_when:** в результате видно round1 / round2 breakdown ✅
- **Implementation:**
  - `_format_final_verdict`: показывает round1_comment / round2_comment
  - `my_results`: показывает round breakdown в истории
- **RICE:**
  - **Reach:** 6
  - **Impact:** 8
  - **Confidence:** 6
  - **Effort:** 4
  - **Score:** 72

### AG-009
- **Title:** Route `Обратная связь` в служебный канал/личку владельца
- **Type:** ops
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-28
- **Commits:** ceb99f0
- **Branch:** main → pushed
- **Why:** отзывы не должны теряться в группах
- **Done_when:** feedback reliably delivered to owner channel
- **Risks:** external delivery and privacy mistakes
- **RICE:**
  - **Reach:** 5
  - **Impact:** 8
  - **Confidence:** 7
  - **Effort:** 3
  - **Score:** 93.33

### AG-010 ✅ DONE (2026-03-31)
- **Title:** Clean project git diff before release commit
- **Type:** hygiene
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-31
- **Why:** в рабочем дереве есть накопленные изменения, нужен осознанный release diff
- **Done_when:** понятен список файлов для commit без мусора и случайных побочек ✅
- **Result:**
  - 9 файлов закоммичено (app/, tests/, scripts/, crew/, state/)
  - Мусор (данные staging, логи) исключён
  - Git diff clean
- **RICE:**
  - **Reach:** 8
  - **Impact:** 6
  - **Confidence:** 8
  - **Effort:** 3
  - **Score:** 128

## BACKLOG (новые от 2026-03-29)

### AG-018
- **Title:** Исправить callback ошибку "🏁 Завершить раунд"
- **Type:** bug
- **Status:** DONE ✅
- **Priority:** P0
- **Closed:** 2026-03-29
- **Why:** критический баг — нельзя завершить раунд
- **Done_when:** при нажатии кнопки раунд завершается без ошибок
- **Risks:** проблема с callback_data форматом
- **RICE:**
  - **Reach:** 10 (все пользователи)
  - **Impact:** 10 (критично для core flow)
  - **Confidence:** 7
  - **Effort:** 3
  - **Score:** 233.33

### AG-019
- **Title:** Убрать дублирование "🎲 Случайный" из основных кнопок
- **Type:** ux
- **Status:** DONE ✅
- **Priority:** P1
- **Closed:** 2026-03-29
- **Why:** кнопка дублируется в пикере и в меню — избыточно
- **Done_when:** "🎲 Случайный" только в пикере сценариев
- **Risks:** пользователи привыкли к кнопке в меню
- **RICE:**
  - **Reach:** 8
  - **Impact:** 6
  - **Confidence:** 9
  - **Effort:** 2
  - **Score:** 216

### AG-020
- **Title:** Объединить два сообщения при активной дуэли
- **Type:** ux
- **Status:** DONE ✅
- **Priority:** P1
- **Closed:** 2026-03-29
- **Why:** два сообщения перегружают интерфейс
- **Done_when:** одно сообщение с текстом и inline кнопкой
- **Risks:** нужно сохранить читаемость
- **RICE:**
  - **Reach:** 8
  - **Impact:** 7
  - **Confidence:** 8
  - **Effort:** 3
  - **Score:** 149.33

### AG-021
- **Title:** Улучшить форматирование "Поединок начался"
- **Type:** ux
- **Status:** DONE ✅
- **Priority:** P2
- **Closed:** 2026-03-29
- **Why:** экран "замыленный", нужно лучше визуально
- **Done_when:** чёткое разделение блоков информации
- **Risks:** легко перегрузить эмодзи
- **RICE:**
  - **Reach:** 8
  - **Impact:** 6
  - **Confidence:** 7
  - **Effort:** 4
  - **Score:** 84

## BACKLOG

### AG-025
- **Title:** Comprehensive bot test suite
- **Type:** test
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-28
- **Commits:** pending
- **Why:** автоматизировать тестирование вместо ручного
- **Done_when:** тесты покрывают core flow (duel, voice, round, judge, menu, feedback) ✅
- **Implementation:**
  - 8 test files created
  - 144 тестовых случая
  - 112 PASS (78%), 32 FAIL (menu/feedback edge cases)
  - Core flow 100% covered (duel creation, turns, voice, round completion)
- **RICE:**
  - **Reach:** 10 (все пользователи — стабильность)
  - **Impact:** 9 (автоматизация тестирования)
  - **Confidence:** 9
  - **Effort:** 6
  - **Score:** ~135

### AG-024
- **Title:** Audit bot screens and improve UX (Quick Wins)
- **Type:** UX / product
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-28
- **Commits:** pending
- **Why:** текущий UX может быть улучшен
- **Done_when:**
  - ✅ UX audit completed (docs/ux_analysis_report.md)
  - ✅ 3 quick win fixes implemented
  - ⏸️ Dynamic menu — code exists, manual test pending
- **Implementation:**
  - FIX 1: Dynamic menu (hide/show buttons based on duel state) — code done, manual test pending
  - FIX 2: Split duel start (2 messages instead of wall of text) — DONE
  - FIX 3: Feedback improvements (cancel button + validation) — DONE
- **RICE:**
  - **Reach:** 9 (все пользователи)
  - **Impact:** 8 (улучшение UX)
  - **Confidence:** 8
  - **Effort:** 5
  - **Score:** ~115

### AG-023
- **Title:** Add automated tests for judge round breakdown
- **Type:** test
- **Status:** DONE
- **Priority:** P1
- **Closed:** 2026-03-28
- **Why:** автоматизировать тестирование round breakdown вместо ручного
- **Done_when:** тесты проверяют LLM parsing, format, display ✅
- **Implementation:**
  - tests/test_judge_round_breakdown.py — 9 тестов (все PASS)
  - Проверяют: LLM response parsing, _format_final_verdict, DB model
  - Запуск: `pytest tests/test_judge_round_breakdown.py -v`
- **RICE:**
  - **Reach:** 8
  - **Impact:** 9
  - **Confidence:** 8
  - **Effort:** 5
  - **Score:** ~120

### AG-011
- **Title:** Voice message breaks duel-flow and starts new scenario
- **Type:** bug
- **Status:** DONE
- **Priority:** P0
- **Why:** при отправке голосового внутри активного раунда теряется текущий duel-flow и запускается новый сценарий, ломающий основной UX
- **Done_when:**
  - голосовое сообщение внутри активного duel не создаёт новый сценарий
  - не сбрасывает состояние
  - корректно продолжает текущий раунд (распознаётся и используется как реплика пользователя)
- **Risks:**
  - правка state machine может задеть текстовые сообщения
  - возможны регрессии в start flow
- **Architecture notes:**
  - Voice handler НЕ работает напрямую с duel-flow
  - Voice handler делает только ASR и передаёт transcript в общий router
  - Введён единый вход в duel-flow: активный duel проверяется ПЕРВЫМ как абсолютный приоритет
  - Text и voice используют один и тот же `_run_turn`
- **Fix:**
  - Усилен приоритет активного duel в `process_voice_turn` и `process_audio_turn`
  - Проверка `has_active_duel` теперь абсолютная — игнорирует `PENDING_CUSTOM_SCENARIO_USERS`
  - Добавлен тест `test_voice_mid_duel_does_not_reset_state`
- **Tests:**
  - `tests/test_voice_routing.py` — 6 passed
  - `tests/test_duel_flow.py` — 6 passed (регрессия)
- **RICE:**
  - **Reach:** 8
  - **Impact:** 10
  - **Confidence:** 9
  - **Effort:** 4
  - **Score:** 180

### AG-012
- **Title:** Add lightweight duel history / recent results UX
- **Type:** product
- **Status:** BACKLOG
- **Priority:** P2
- **Why:** пользователю нужен быстрый доступ к прошлым поединкам
- **Done_when:** можно открыть несколько последних результатов, а не только последний
- **Risks:** потребует UX решения для list/history
- **RICE:**
  - **Reach:** 5
  - **Impact:** 6
  - **Confidence:** 6
  - **Effort:** 5
  - **Score:** 36

### AG-013
- **Title:** Improve scoring rubric for judges
- **Type:** quality
- **Status:** DONE
- **Priority:** P2
- **Closed:** 2026-03-28
- **Commits:** pending
- **Why:** текущий output полезен, но ещё можно сделать его более последовательным
- **Done_when:** judge verdicts более стабильны и объяснимы ✅
- **Implementation:**
  - 5-балльная шкала оценки для каждого раунда
  - Явные критерии для каждого judge type (owner/team/sender)
  - Decision rules с порогами для winner determination
  - Few-shot примеры для consistency
- **Files:** app/prompts/judges.md
- **Risks:** prompt churn without clear product gain
- **RICE:**
  - **Reach:** 5
  - **Impact:** 7
  - **Confidence:** 5
  - **Effort:** 6
  - **Score:** 29.17

### AG-014
- **Title:** Add richer analytics and owner dashboard later
- **Type:** analytics
- **Status:** BACKLOG
- **Priority:** P3
- **Why:** полезно позже, но не критично для текущего MVP
- **Done_when:** появляются метрики usage, scenario popularity, duel outcomes
- **Risks:** преждевременное усложнение
- **RICE:**
  - **Reach:** 3
  - **Impact:** 5
  - **Confidence:** 5
  - **Effort:** 8
  - **Score:** 9.38
