# Project Index

## Purpose

- This is the project map
- File needed for navigation across the new structure
- Structure migration is executed step-by-step

## Top-Level Zones

- **crew/** — policy, workflow, role/context files for LLM orchestration
- **state/** — current project state, backlog, devlog
- **product/** — product docs, acceptance, user flow
- **architecture/** — system structure and technical design
- **docs/** — supporting technical docs, baselines, analyses
- **memory/** — daily/project memory notes
- **app/** — application code

## Bootstrap

**PROJECT_CONTEXT_SUMMARY.md** is the bootstrap entrypoint and stays in the repository root.

## Migration Status

- [x] migration branch created
- [x] working tree cleaned before migration
- [x] target directories scaffold created
- [x] root md files moved into target zones
- [x] path references updated
- [x] migration finalized

## Reading Strategy

1. Start with PROJECT_CONTEXT_SUMMARY.md
2. Use PROJECT_INDEX.md to locate the right zone
3. Read only the files needed for the current task
4. Prefer current state files over historical notes when they conflict

## Notes

Migration completed 2026-03-28. All project files organized into target zones.
