---
title: "Competitor source review: prime-radiant-inc/iterative-development"
date: 2026-07-12
files_read:
  - README.md
  - ABOUT.md (not opened; README + design spec superseded it)
  - .claude-plugin/plugin.json
  - skills/iterative-development/SKILL.md
  - skills/extracting-requirements/SKILL.md
  - skills/scoping-the-simplest-core/SKILL.md
  - skills/running-an-iteration/SKILL.md
  - skills/implementing-tasks/SKILL.md
  - skills/auditing-progress/SKILL.md
  - skills/shared/parallel-adversarial-review.md
  - skills/shared/par-reviewer-wrapper.md
  - skills/shared/behavior-evidence-formats.md
  - docs/superpowers/specs/2026-04-05-iterative-development-design.md
  - docs/superpowers/plans/2026-04-05-plan-06-autonomy.md (implementation-plan draft of the orchestrator skill, superseded by the current SKILL.md but useful for design history)
  - full repo file tree via GitHub API (git/trees/main?recursive=1)
secondary_target_reviewed: false
note: >
  gmickel's flow-next was not reached — time went entirely into reading
  iterative-development's actual source rather than skimming both. The
  verdict below stands on iterative-development alone.
---

# What it actually is (from source)

**Six skills, no hooks, no commands, no scripts driving control flow.** `.claude-plugin/plugin.json` declares only a `components.skills` array (six skill directories); there is no `hooks` or `commands` key. All control flow — the `while True` loop, the gate sequencing, the escalation policy — lives as prose inside `SKILL.md` files, executed by model discretion. The only scripts (`chunk_spec.py`, `aggregate_stories.py`, `aggregate_scenarios.py`, `backlink_scenarios.py`, `check_citations.py`, `validate_roadmap.py`, `validate_iteration_log.py`) are mechanical format/citation validators, not orchestrators — same shape as our own conductor-in-markdown approach.

**The loop** (`skills/iterative-development/SKILL.md`):
```
while True:
    check_for_human_interrupt()
    if not roadmap has pending iterations:
        if last audit was clean: break
    run next iteration: running-an-iteration
    audit: auditing-progress
        if gaps: append to backlog, revise roadmap, continue
        if clean: mark last_audit_clean, continue
```
Six skills, each a phase:
- `extracting-requirements` — chunks arbitrary human spec prose (`journeys/`, `contracts/`, `domains/`, `test-vectors/` directories map to default proof seams), dispatches parallel extraction subagents, aggregates into `requirements/` (per-epic story cards) + `behavior-scenarios.md` + `behavior-corpus.md`.
- `scoping-the-simplest-core` — picks a walking-skeleton iteration (ITER-0000) that must close at least one journey scenario, orders the rest into iterations, splits stories with heterogeneous-dependency ACs.
- `running-an-iteration` — one iteration: sentinel baseline → pre-iteration PAR scope review → decompose into code+evidence tasks → dispatch `implementing-tasks` → post-iteration impacted+sentinel scenario reruns → grep for unresolved `TODO(ITER-<current>)` stubs → wrap up (mark stories done, update roadmap/log).
- `implementing-tasks` — explicitly "a fork of `superpowers:subagent-driven-development` with the plan-file reading phase stripped and the final end-of-plan reviewer removed." Per task: implementer subagent → PAR spec-compliance review → PAR code-quality review (with a "boxing-in" check against the next 3 iterations) → mark done.
- `auditing-progress` — after **every** iteration, PAR paired auditors across three tiers (deep evidence for this iteration's new work, impacted-behavior sweep, sentinel-corpus regression check). Gaps get written back into the backlog.

# R1–R7 fit table

| Req | Verdict | Evidence |
|---|---|---|
| **R1** — gates are generative (review writes new backlog rows) | **Already matches, near drop-in** | `auditing-progress/SKILL.md` step 4: "If gaps found... append gap stories to `requirements/` (status `pending`)... Revise `roadmap.md` to add a follow-up iteration for the gaps." This is the exact mechanism R1 asks for — audit output is a diff against the backlog, not just a report. |
| **R2** — scope growing at pull time is the *normal* path, not an error | **Resists.** Gate 1 (pre-iteration scope review) is named and framed explicitly as scope-creep *prevention*: `running-an-iteration/SKILL.md` step 5 runs PAR "following the scope reviewer prompt" whose job includes catching "does this iteration try to do too much?" The design spec calls this gate's purpose "citation integrity + scope-creep prevention + boxing-in look-ahead" — growth is something to catch and revise back down, never a modeled, expected, mid-sprint event. The nearest analog is task-splitting under implementer `BLOCKED` handling, which manages a single oversized task, not a sprint whose scope legitimately doubles against live code. |
| **R3** — hard autonomous boundary: run everything provable to completion, then HARD STOP at human-needed work, as the *target shape* | **Actively resists — this is the core conflict.** `iterative-development/SKILL.md` Escalation Policy: *"Catastrophe-only... Ambiguity in the spec (make a reasonable judgment call...) ... Difficulty or slow progress (keep going)... The orchestrator does NOT prompt 'should I continue?' between iterations."* The design spec lists this as Core Principle #9, "Autonomous by default." There is no concept of a legitimate, planned stopping point for work that only a human can do — the design's stated goal is the *opposite* of R3: never stop except total failure. |
| **R4** — distinguish backlog-amending replans from backlog-superseding resets | **Unresolved — the authors punted on it too.** Design spec, "Open design decisions": *"Roadmap revision mechanism after audit. When the audit finds gaps and the roadmap needs to be revised, what's the formal mechanism? Inline edit... a dedicated `revising-the-roadmap` step, or re-run `scoping-the-simplest-core`...? Implementation-dependent choice."* No north-star-change / superseding-reset concept appears in any file read. |
| **R5** — escalation is out-of-band (blocker file + stop) because AskUserQuestion is stripped from subagents / auto-answers empty headless | **Actively resists — wrong interaction model entirely.** The Human Interrupt Protocol is explicitly **in-band chat**: *"The human types the update into the chat session running the orchestrator... Human presence is not required at iteration boundaries; interrupts are opportunistic."* There is no file-based blocker/signal mechanism anywhere in the repo. The whole design assumes a live human co-present in the same interactive session as the orchestrator — it has no answer for headless/subagent execution at all. |
| **R6** — survive the conductor's own context death; resumable mid-sprint | **Good fit, though by side effect not intent.** Core Principle #8: *"Evergreen state in artifacts... there is no ephemeral in-memory orchestrator state that would be lost across crashes or sessions."* `iterative-development/SKILL.md`: *"the command 'continue iterative development with the existing plan' always works."* This satisfies R6's letter even though the design frames it as crash-recovery, not as a deliberately scheduled context-refresh rhythm (unlike our GATE → fresh context → GATE cycle, which is load-bearing by design, not a fallback). |
| **R7** — scratch-dir namespacing per sprint is structural, not conventional | **Missing.** No per-iteration scratch-directory concept exists. `extracting-requirements/SKILL.md` step 2 tells subagents to "persist immediately... to a temp file (e.g., a scratch directory under the project root)" with zero namespacing rule — same collision class our own memory [[sdd-scratch-dir-collides-across-sprints]] warns about. Iteration artifacts themselves are flat singleton files (`roadmap.md`, `iteration-log.md`, `behavior-scenarios.md`), not per-sprint directories. |

# Verdict + reasoning

**BUILD STANDALONE** — but salvage specific mechanisms, don't fork the trunk.

The single strongest piece of evidence: R3 and R5 aren't gaps you patch, they're **named core principles the authors deliberately built the opposite of.** Design spec Core Principle #9 is literally titled "Autonomous by default" and defines escalation as catastrophe-only; the Human Interrupt Protocol is titled "out-of-band" in their own doc but actually means "the human types into the same live chat session" — the opposite of what "out-of-band" means for us (headless subagents whose `AskUserQuestion` is stripped). Making iterative-development support supskill's mandatory dual human gate per sprint and a hard-stop-at-human-work boundary means rewriting the one skill (`iterative-development/SKILL.md`) that defines the plugin's identity, plus its Escalation Policy and Human Interrupt Protocol sections wholesale. That's not "surgery on a fork," that's replacing the spine.

Compounding this: the **input model runs backwards from ours.** iterative-development exists to *extract* a backlog from raw prose spec collateral (`extracting-requirements` + `scoping-the-simplest-core`, half its skill count) — we already have a markdown backlog and need a conductor to *drive* it. Those two skills are dead weight for us. The remaining three (`running-an-iteration`, `implementing-tasks`, `auditing-progress`) are tightly coupled to their story/scenario/proof-obligation schema (`STORY-NNNN`, `SCENARIO-NNNN`/`JOURNEY-NNNN`, `impact:`/`seam:` annotations) — adopting them means either reformatting our backlog into their schema or rewriting the skills to not need it, which is most of the surgery a "FORK" would require anyway.

R1 and R6 are the two requirements it already satisfies cleanly, and they're the two least distinctive to our design — most competent audit-loop systems land there. The requirements that actually define *why* supskill exists (R2's normal-path scope growth, R3's hard-stop-as-target-shape, R5's headless-safe escalation) are the ones it either fights or never solved.

# Ideas worth stealing

1. **Parallel Adversarial Review (PAR)** — dispatch two reviewer subagents on identical inputs, wrap both in a fixed competitive-scoring frame ("5 points per serious/critical finding, nitpicks don't count, false positives are worse than misses"), and aggregate with a fixed rule: same finding from both → high confidence; finding from one → still actionable; severity disagreement → always take the worse one, no negotiation. `skills/shared/par-reviewer-wrapper.md` is a ready-to-copy prompt template. This is a concrete, cheap countermeasure to reviewer sycophancy we should use at our own sprint-review gates.
2. **The generative-audit mechanism itself (R1's actual implementation)** — worth lifting verbatim as a pattern: audit output isn't a report, it's a diff against the backlog file (new `pending` rows appended, `roadmap.md` gets a follow-up iteration inserted). Steal the mechanical shape even though we're building the rest standalone.
3. **Proof-seam taxonomy + per-AC evidence annotation** (`impact: none|local|cross-surface|journey`, `seam: unit|integration|app-level|process-level|e2e`, mandatory `scenario:` ref unless impact is none) from `skills/shared/behavior-evidence-formats.md`. This is a disciplined way to make "done" mean "evidence exists at the right seam," which maps onto our own need to know what's actually offline-provable vs. needs a human (R3) — their taxonomy is a good starting vocabulary even though their loop never stops for the human parts.
4. **"Harness-first" walking skeleton rule**: the walking skeleton's first task must be designing the E2E test harness, before any feature work, using their "Test Infrastructure Checklist" (launch/teardown, input simulation, state observation, external-dependency fixturing, manual-residual documentation). Forces infra debt to surface at sprint 0 instead of iteration 8.
5. **Cross-iteration `TODO(ITER-N)` stub-resolution gate** (`running-an-iteration/SKILL.md` step 9): grep for forward-reference stubs left by earlier iterations expecting the *current* iteration to fill them in; unresolved stub = iteration isn't done, full stop. A concrete technique for the "story references a subsystem that doesn't exist yet" problem without boxing in early sprints — useful independent of their broader anti-scope-growth stance.
