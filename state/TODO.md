# Agon Arena — TODO / BACKLOG

Лёгкий рабочий backlog для текущего MVP.

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

### AG-006
- **Title:** Commit and push validated release after manual PASS
- **Type:** release
- **Status:** TODO
- **Priority:** P0
- **Why:** по local policy задача полностью завершается только после release + push
- **Done_when:** есть commit, push, evidence по branch/hash
- **Risks:** случайно включить мусорный diff
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
- **Status:** TODO
- **Priority:** P1
- **Why:** пользователю полезно понимать, что было сильным/слабым в каждом раунде отдельно
- **Done_when:** в результате видно round1 / round2 breakdown
- **Risks:** может затронуть prompts and formatting
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

### AG-010
- **Title:** Clean project git diff before release commit
- **Type:** hygiene
- **Status:** TODO
- **Priority:** P1
- **Why:** в рабочем дереве есть накопленные изменения, нужен осознанный release diff
- **Done_when:** понятен список файлов для commit без мусора и случайных побочек
- **Risks:** можно случайно выкинуть нужные изменения
- **RICE:**
  - **Reach:** 8
  - **Impact:** 6
  - **Confidence:** 8
  - **Effort:** 3
  - **Score:** 128

### AG-015
- **Title:** Analyze token efficiency across development pipeline
- **Type:** analysis
- **Status:** TODO
- **Priority:** P1
- **Why:** нужно оценить, где теряются токены в pipeline (PM/ANALYST/DEV/ARCH/TEST + delivery)
- **Done_when:**
  - проанализирован расход токенов на каждом этапе pipeline
  - выявлены потери: лишние вопросы, дублирование, verbose formatting
  - рекомендованы оптимизации (без реализации пока)
- **Risks:** analysis может затянуться без чётких метрик
- **RICE:**
  - **Reach:** 9
  - **Impact:** 7
  - **Confidence:** 6
  - **Effort:** 4
  - **Score:** 94.5
- **Note:** Сначала analysis phase. Потом решение: отдельная роль или использование ANALYST.

## BACKLOG

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
- **Status:** BACKLOG
- **Priority:** P2
- **Why:** текущий output полезен, но ещё можно сделать его более последовательным
- **Done_when:** judge verdicts более стабильны и объяснимы
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
