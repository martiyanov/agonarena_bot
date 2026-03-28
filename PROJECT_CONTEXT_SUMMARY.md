# PROJECT CONTEXT SUMMARY

Быстрое восстановление контекста при старте сессии.

## CURRENT_TASK
- title: AG-009 — Route `Обратная связь` to owner channel
- status: DONE
- stage: OWNER_SUMMARY delivered
- last_result: TEST PASS, 5/5 scenarios, config system fix

## NEXT_ACTION
- Предложить следующую задачу (AG-009 или AG-015)
- Ожидать решения пользователя

## PIPELINE_STATUS
- last_stage: TEST PASS → OWNER_SUMMARY
- stall: no
- last_success: AG-010 (2026-03-28)

## ACTIVE_RULES
- PM — единая точка входа/выхода
- MANDATORY_DOCUMENTATION_UPDATE (§16) — обязательно после каждой задачи
- CONTEXT_LOADING_POLICY (§17) — читать только этот файл при старте
- THINKING_MODE_CONTROL (§18) — EXECUTION/ANALYSIS/FREE режимы
- READY_FOR_TEST обязателен после DEV
- DELIVERY_SINGLE_SOURCE_OF_TRUTH — message для Telegram, sessions_send для internal
- LANGUAGE: русский для user-facing

## ROLE_MODELS
- PM: modelstudio/qwen3.5-plus (или kimi-k2.5 по запросу)
- DEV: modelstudio/qwen3-coder-plus (или kimi-k2.5 по запросу)
- TEST: modelstudio/qwen3-coder-plus (или kimi-k2.5 по запросу)
- ANALYST: modelstudio/qwen3.5-plus — on-demand (UX, A/B)
- ARCH: modelstudio/qwen3-max-2026-01-23 — on-demand (architecture >100 LOC)
- fallback: kimi-k2.5 при явном запросе пользователя

## RECENT_CHANGES
- AG-009: Route feedback to owner — DONE (config system fix)
- AG-018: Fix "Завершить раунд" button registration — DONE (keyboard visibility)
- AG-017: Fix "Завершить раунд" button — DONE (critical P0 bug)
- AG-015: Analyze token efficiency — DONE (20-25% reduction target)
- AG-010: Clean git diff — DONE (tested Kimi 2.5)
- AG-006: Release commit — DONE (retroactive docs update)
- Policy v1.19: MANDATORY_DOCUMENTATION_UPDATE added
- Policy v1.20: CONTEXT_LOADING_POLICY added
- Policy v1.21: THINKING_MODE_CONTROL added

## BACKLOG_TOP
1. AG-012 (P2) — Duel history UX (backlog)
2. AG-013 (P2) — Improve scoring rubric (backlog)
3. AG-014 (P3) — Analytics dashboard (backlog)

## KNOWN_ISSUES
- None — все P0 задачи закрыты

---

Updated: 2026-03-28
Version: 1.7
