# PROJECT CONTEXT SUMMARY

**Bootstrap file for starting a new LLM session.**

---

## PURPOSE

This file is your entrypoint when starting a session. Read this first, then PROJECT_INDEX.md, then only the files relevant to your current task. Keep this file short and refresh it regularly.

---

## CURRENT_PROJECT_STATE

**Project:** Agon Arena — Telegram bot for managerial duel practice

**Status:** MVP in active polishing phase

**Current phase:** Post-migration cleanup + feature stabilization

**What matters now:**
- Structure migration complete (2026-03-28)
- All files organized into zones: crew/, state/, product/, architecture/, docs/
- Git workflow simplified to DIRECT_MAIN by default
- Core duel-flow is stable and tested

---

## NAVIGATION

| Zone | Purpose |
|------|---------|
| **PROJECT_INDEX.md** | Project map + zone navigation |
| **crew/** | Policy, workflow, role files (AGENT_POLICY.md, SOUL.md, etc.) |
| **state/** | Current state, backlog, devlog (TODO.md, PROJECT_STATE.md, DEVLOG.md) |
| **product/** | Product docs (PROJECT.md, ACCEPTANCE.md, USER_FLOW.md) |
| **architecture/** | System structure (ARCHITECTURE.md) |
| **docs/** | Reference docs, baselines, analysis |
| **memory/** | Daily memory notes (historical, local) |
| **app/** | Application code |

---

## SESSION_START_RULE

1. **Start here** — read this file
2. **Read PROJECT_INDEX.md** — understand project structure
3. **Read only what's relevant** — use zones to locate needed files
4. **Prefer current state** — state/* files over historical notes when they conflict

---

## CURRENT_FOCUS

**Completed:**
- ✅ Structure migration (all files in target zones)
- ✅ Git workflow policy simplified (DIRECT_MAIN default)
- ✅ Core duel-flow stable (tests passing)
- ✅ Telegram UX working (scenario picker, round buttons, voice input)

**No urgent structural changes needed:**
- Policy is current (v1.18)
- Structure is stable
- No P0 bugs open

**Next logical work classes:**
- Feature backlog (duel history UX, scoring rubric improvements)
- Polish + refinements based on user feedback
- Technical debt cleanup (if identified)

---

## ACTIVE_POLICY_HIGHLIGHTS

**Operational rules (from crew/AGENT_POLICY.md):**

1. **PM = single entry/exit** — All coordination through PM role
2. **THINKING_MODE_CONTROL** — EXECUTION (default), ANALYSIS, FREE modes
3. **DIRECT_MAIN git workflow** — Work in main by default, commit + push after task
4. **SAFE_BRANCH only for risky work** — migration, large refactor, experimental changes
5. **Mandatory documentation updates** — Update state/* files after meaningful changes
6. **Chinese stack priority** — ModelStudio models default (qwen3.5-plus, qwen3-coder-plus)

---

## NOTES

- **memory/*.md** are historical/local continuity notes — read for context, don't treat as source of truth
- **PROJECT_CONTEXT_SUMMARY.md** should stay short — refresh this file every few sessions
- **When in doubt** — check crew/AGENT_POLICY.md for operational rules, state/TODO.md for backlog

---

**Updated:** 2026-03-28  
**Version:** 2.0 (post-migration refresh)
