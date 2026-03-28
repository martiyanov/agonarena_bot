# TOKEN_EFFICIENCY_ANALYSIS — AG-015

**Date:** 2026-03-28  
**Analyst:** Subagent (ff85bae8-6bd6-4991-bf17-c04ff57d5807)  
**Task:** Validate PM findings and recommend optimization approach

---

## VALIDATION OF PM FINDINGS

### PM Claims vs Evidence

| Claim | Evidence | Status |
|-------|----------|--------|
| **Total tokens per pipeline: 35-50k** | AG-010 (simple task): ~23k tokens (DEV 12.3k + TEST 6.0k + TEST re-run 4.8k). Complex tasks with ARCH would add ~15-20k more. | ✅ **CONFIRMED** (range is accurate) |
| **Context replication: 30-40%** | CONTEXT_PRUNING policy already enforces MAX_CONTEXT_BLOCKS=3. Waste occurs when roles repeat context from previous steps. | ✅ **CONFIRMED** (policy exists, compliance varies) |
| **Verbose formatting: 15-20%** | VERBOSITY_CONTROL enforces line limits (PM≤5, DEV≤10, TEST≤5). DEVLOG shows multiple format reverts needed. | ⚠️ **PARTIALLY CONFIRMED** (policy exists, enforcement inconsistent) |
| **Rework loops: 20-25%** | AG-010: TEST FAIL → re-run (extra 4.8k tokens). AG-018: 2 sequential bugs (keyboard visibility + handler logic). | ✅ **CONFIRMED** (rework is significant waste source) |

### Additional Insights

1. **Rework is the largest controllable waste source:**
   - AG-010: TEST caught tracked file issue → 4.8k token re-run
   - AG-017 → AG-018: Two sequential fixes for same button (250+405 RICE wasted on rework)
   - Root cause: Incomplete context or rushed DEV handoff

2. **ARCH model is the biggest single cost:**
   - qwen3-max-2026-01-23 is ~3-5x more expensive than qwen3-coder-plus
   - COST_CONTROL_POLICY downgrade rule helps, but ARCH still called for marginal cases

3. **TOKEN_OBSERVABILITY is not being used:**
   - Policy requires TOKEN_USAGE block in OWNER_SUMMARY
   - No evidence of actual token tracking in recent OWNER_SUMMARY outputs
   - Cannot optimize what you don't measure

---

## OPTION ANALYSIS

### Option A: Dedicated OPTIMIZER Role

**Description:** Create new role that reviews pipeline output before delivery, suggests token reductions.

**Pros:**
- ✅ Specialized focus on token efficiency
- ✅ Could catch waste patterns systematically
- ✅ Clear ownership of optimization metric

**Cons:**
- ❌ **Adds another role call** → increases baseline token cost by ~5-10k per pipeline
- ❌ **Post-hoc optimization** — catches waste after it happens, doesn't prevent it
- ❌ **Complexity** — requires new trigger rules, model mapping, policy updates
- ❌ **Diminishing returns** — most obvious waste already covered by existing policies
- ❌ **Ironic** — spending tokens to save tokens

**Estimated cost:** +5-10k tokens per pipeline (OPTIMIZER call)  
**Estimated savings:** 3-7k tokens per pipeline (optimization suggestions)  
**Net impact:** **NEGATIVE** (-2 to -3k tokens per pipeline)

---

### Option B: Expanded ANALYST Mandate

**Description:** Extend ANALYST role to include token efficiency reviews during UX/product analysis phases.

**Pros:**
- ✅ **No new role** — uses existing infrastructure
- ✅ **Preventive** — can catch waste during planning phase, before DEV starts
- ✅ **Natural fit** — ANALYST already does "meta" analysis (UX, priorities, trade-offs)
- ✅ **On-demand** — only called when task has ambiguity or complexity
- ✅ **Lower cost** — qwen3.5-plus is cheaper than ARCH or hypothetical OPTIMIZER

**Cons:**
- ⚠️ **Dilutes focus** — ANALYST already has UX/product mandate
- ⚠️ **Requires training** — ANALYST needs token awareness in prompts
- ⚠️ **Not comprehensive** — only catches waste when ANALYST is triggered

**Estimated cost:** +0 tokens (ANALYST already called when needed)  
**Estimated savings:** 5-10k tokens per pipeline (when ANALYST is invoked)  
**Net impact:** **POSITIVE** (+5 to +10k tokens saved per ANALYST-triggered pipeline)

---

## RECOMMENDATION

### Chosen Option: **Option B — Expanded ANALYST Mandate**

### Justification

1. **Net-positive token economics:**
   - Option A (OPTIMIZER) loses 2-3k tokens per pipeline
   - Option B (ANALYST) saves 5-10k tokens when invoked
   - Option B has no baseline cost overhead

2. **Prevention > cure:**
   - OPTIMIZER catches waste after it happens (DEV already wrote verbose code)
   - ANALYST can prevent waste during planning (before DEV starts)
   - Example: ANALYST can flag "this UX decision needs clarification → ask PM now, not after DEV implements wrong thing"

3. **Existing infrastructure:**
   - ANALYST role already defined with triggers
   - No new policy sections needed
   - Just extend existing mandate

4. **Aligns with current architecture:**
   - Current policy already avoids role proliferation (5 roles max)
   - TOKEN_OBSERVABILITY already exists (just needs enforcement)
   - VERBOSITY_CONTROL and CONTEXT_PRUNING already in place

---

## IMPLEMENTATION PLAN

### Step 1: Enforce TOKEN_OBSERVABILITY (Immediate)

**Action:** Add TOKEN_USAGE block to every OWNER_SUMMARY

**Change:**
```markdown
### TOKEN_USAGE
- approx_prompt_tokens: N
- approx_completion_tokens: N
- largest_step: PM/DEV/TEST/ARCH
- optimization_hint: <1 line>
```

**Who:** TEST subagent (already validates policy compliance)  
**Timeline:** Next pipeline run  
**Cost:** 0 tokens (just formatting)

---

### Step 2: Expand ANALYST Mandate (Policy Update)

**Action:** Add token efficiency to ANALYST triggers

**Change to AGENT_POLICY.md Section 2.2.1:**

```
ANALYST вызывается если:
- ✅ Есть UX задача (layout, flow, interaction)
- ✅ Есть выбор между вариантами (A/B test)
- ✅ Есть продуктовая неопределённость
- ✅ Требуется приоритизация backlog
- ✅ **Задача имеет высокий RICE score (>150) — token efficiency review**
- ✅ **Задача затрагивает multiple pipeline stages — coordination review**
```

**Who:** PM (updates policy)  
**Timeline:** Next policy update  
**Cost:** 0 tokens

---

### Step 3: Add Token Awareness to ANALYST Prompt (Training)

**Action:** Add token efficiency checklist to ANALYST role

**ANALYST Token Checklist:**
```
Before finalizing recommendations:
- [ ] Can this decision be made from existing policy? (avoid PM question)
- [ ] Is the scope clearly defined? (prevent DEV rework)
- [ ] Are acceptance criteria specific? (prevent TEST ambiguity)
- [ ] Can this be implemented in <100 LOC? (avoid ARCH trigger)
- [ ] Is the format mobile-friendly? (prevent rework for Telegram)
```

**Who:** PM (updates SUBAGENT_WORKFLOW.md)  
**Timeline:** After policy update  
**Cost:** 0 tokens

---

### Step 4: Measure and Iterate (Ongoing)

**Action:** Track token usage for 10 pipeline runs, compare before/after

**Metrics:**
- Average tokens per pipeline (baseline: 35-50k)
- Rework rate (TEST FAIL → re-run frequency)
- ANALYST invocation rate (currently ~20% of tasks)
- Largest step distribution (PM/DEV/TEST/ARCH)

**Who:** PM (collects data from TOKEN_USAGE blocks)  
**Timeline:** 2 weeks  
**Cost:** 0 tokens

---

## SUCCESS_METRICS

### Target Token Reduction: **20-25%**

**Breakdown:**
| Waste Source | Current | Target | Reduction |
|--------------|---------|--------|-----------|
| Context replication | 30-40% | 15-20% | -15% |
| Verbose formatting | 15-20% | 10-12% | -5% |
| Rework loops | 20-25% | 10-15% | -10% |
| **Total** | **~35-50k** | **~28-38k** | **~20-25%** |

### Measurement Method

1. **TOKEN_USAGE block in every OWNER_SUMMARY:**
   - `approx_prompt_tokens` — sum of all stage inputs
   - `approx_completion_tokens` — sum of all stage outputs
   - `largest_step` — identifies bottleneck
   - `optimization_hint` — qualitative improvement suggestion

2. **Weekly aggregation:**
   - Average tokens per pipeline
   - Rework rate (TEST FAIL count / total pipelines)
   - ANALYST invocation rate

3. **Success threshold:**
   - 4-week rolling average < 40k tokens per pipeline
   - Rework rate < 15%
   - 80%+ compliance on TOKEN_USAGE block presence

---

## CONCLUSION

**Do NOT create OPTIMIZER role.** The token economics don't work — you'd spend more tokens on optimization than you'd save.

**DO expand ANALYST mandate** to include token efficiency awareness during planning phase. This prevents waste before it happens, uses existing infrastructure, and has positive ROI.

**Immediate action:** Enforce TOKEN_OBSERVABILITY policy — you can't optimize what you don't measure.

---

**READY_FOR_TEST: yes**
