# supskill — Backlog 01: the conductor

**Date:** 2026-07-12 · Legend: points = Fibonacci · pri = MoSCoW (M/S/C/W) · status ☐ todo / ◐ wip / ☑ done / ⊘ blocked

Derived from [2026-07-12-supskill-design-decisions.md](../../../.ai/reports/2026-07-12-supskill-design-decisions.md)
(approved 2026-07-12). Decision references below (**D1**–**D9**) point at that file; do not re-litigate
a decision without amending it there first.

---

## North star

> A conductor that drives **one sprint** from a markdown backlog to a merged branch — drawing a fresh
> context boundary at every stage, holding three human gates, and keeping all authoritative state on
> disk so it survives its own context death.

The product is **the boundaries, the gates, and the escalation**. Not a methodology.

## Inviolable invariants (locked; do not design a seam that weakens these)

1. **Compose, never reinvent.** supskill orchestrates `pm-execution:sprint-plan`,
   `superpowers:writing-plans`, and `superpowers:subagent-driven-development`. It contributes no
   opinion about how code gets written. The moment a story starts reimplementing one of these, it is
   out of scope. (**D1**)
2. **Escalation is out-of-band, always.** `AskUserQuestion` is *stripped* from subagents and in
   headless/no-TTY **auto-resolves in ~37ms with an EMPTY answer** — intentionally, issue closed "not
   planned". A delegated agent can therefore never ask the operator anything. Any story whose design
   assumes it can is wrong. (**D4**)
3. **The script is the only mutator of `state.json`.** Every transition validates preconditions. The
   model may not advance a stage the script refuses. (**D2**)
4. **Scratch paths are derived, never typed.** The `.superpowers/sdd/<sprint-id>/` collision must be
   structurally impossible, not conventionally avoided. (**D8**)
5. **The conductor is disposable.** It holds no state in its head; `/clear` + re-invoke resumes
   mid-sprint from disk. Any in-memory-only state is a bug.
6. **One sprint per invocation.** Plans go stale. No look-ahead planning. (**D6**)
7. **The conductor never supersedes a backlog on its own.** A north-star reset is operator-authored,
   full stop. (**D7** / four replan shapes)

## Findings that shape the plan (verified; see `docs/.ai/reports/contexts/`)

- **F-1 (the chain does not actually compose).** `sprint-plan` emits stories/points/risks;
  `writing-plans` expects a *spec* and assumes it came from `brainstorming`. The bridge that works in
  practice is the undocumented "DoR findings (refined at pull time)" pass — present in every blinkebot
  sprint doc, and the reason committed points grew *every single sprint* (10→16, 14→16, 18→23).
  → **E3, and it is the heart of the product.** (**D3**)
- **F-2 (the executor already speaks our language).** SDD reports
  `DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT` per task. We adopt it verbatim; we do not
  invent a parallel protocol. → **E5.** (**D5**)
- **F-3 (nested subagents work).** Shipped v2.1.172, depth cap 5. The widely-cited GitHub issue
  saying otherwise is **stale**. The conductor may dispatch SDD, which dispatches its own task agents
  (depth 2 of 5). Do not re-derive the old, wrong constraint.
- **F-4 (gate enforcement has a real ceiling).** The script cannot prove a *human* answered a gate. It
  makes skipping **loud and auditable**, not impossible. Do not write a story that claims otherwise.
- **F-5 (agents are poor self-certifiers).** blinkebot S9 shipped green — 410 tests — and its
  whole-branch review still found five mechanisms with **zero production callers**. Single-reviewer
  sign-off is not trustworthy. → **E6 / PAR.** (**D9**)

---

## Summary — epics, in recommended build order

| # | Epic | Why it's here | Pts | Pri |
|---|------|---------------|-----|-----|
| **E1** | **The state spine** | Everything compounds on it, it is the only pure-Python unit-testable part, and it kills the scratch-dir ritual structurally. Do FIRST. | 18 | **M** |
| **E2** | **Conductor skill + plugin skeleton** | The disposable conductor: invoke, read state, resume. Nothing runs without it. | 12 | **M** |
| **E3** | **SCOPE + REFINE + Gate 1** | The refine-at-pull-time stage. The bridge (F-1) and the proof-seam classification that Gate/E5 depend on. **The heart.** | 23 | **M** |
| **E4** | **PLAN + Gate 2** | Thin in code, sharp in consequence: wiring `writing-plans` and stopping it from executing the sprint it is planning. | 14 | **M** |
| **E5** | **EXECUTE (drain-then-halt)** | Where autonomy actually pays, and where silent guessing must be made impossible. | 23 | **M** |
| **E6** | **REVIEW (PAR) + Gate 3 + replan shapes** | The generative gate — the one that writes the next sprint. Highest value, highest complexity. | 27 | **M** |
| **E7** | **Packaging & distribution** | Marketplace, trigger-only description, evals. | 9 | **S** |
| **E8** | **Validation** | Earns its keep or does not ship. | 10 | **M** |

**Total: 136 pts for v1 (E1–E8, all shipped), plus 70 pts of E9 post-validation findings
and 30 pts of E10 operator-interaction work.**
Expect this to grow — every blinkebot sprint grew its committed points at DoR
refinement, and there is no reason to believe this project is the exception. That growth is the
process working, not a planning failure. E9 is the exception's proof: the real runs turned the
same discipline on supskill and found 70 points of real work, filed rather than remembered.

---

## E1 — The state spine (18 pts)

The walking skeleton. Harness-first: this epic ends with a real, fast, offline test suite proving the
gates cannot be skipped.

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-001 | `state.json` schema v1 + typed read/write. Round-trips every field in **D2**'s schema. | 3 | M | ☑ |
| SK-002 | `supskill-state init \| show`. Creates a sprint run; prints current stage/gates/tasks. | 2 | M | ☑ |
| SK-003 | `supskill-state advance --to <STAGE>` **with precondition validation**. Refuses `PLAN` without `G1 == approved`; refuses `EXECUTE` without `G2 == approved`; refuses `REVIEW` while any task is non-terminal. **This is the enforcement mechanism — the single most important story in the backlog.** | 5 | M | ☑ |
| SK-004 | Derive `sprint.scratch` from sprint id. `s9` and `s9a` must produce different paths. Kills the hand-copied ritual. (**D8**) | 2 | M | ☑ |
| SK-005 | `supskill-state gate --id G1 --decision <d> --response <verbatim>` → appends to `gates.jsonl`. The audit trail is the whole point; a fabricated approval must leave a readable trace. (F-4) | 3 | M | ☑ |
| SK-006 | `supskill-state block` → blocker record → `runs/<sprint-id>/blockers.jsonl`. Schema **requires** `options[]` and `recommend`; reject a record without them. (**D5**) | 3 | M | ☑ |

**DoR note:** SK-003 and SK-006 carry the design's two load-bearing constraints. Refine both against
the real SDD output format before committing points.

## E2 — Conductor skill + plugin skeleton (12 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-010 | Plugin skeleton: `.claude-plugin/plugin.json`; components (`skills/`, `agents/`, `scripts/`) at plugin **root**, not inside `.claude-plugin/`. | 2 | M | ☑ |
| SK-011 | `SKILL.md` whose `description` states **only triggering conditions** and does **not** summarize its own workflow — a documented regression causes agents to skip half the process otherwise. Decided at S2 DoR: v1 is user-invoked only (`disable-model-invocation: true`) because the conductor is side-effecting; SK-061 inherits the flagged tension. | 3 | M | ☑ |
| SK-012 | Conductor resumes from `state.json` alone. `show` grows `artifacts` + `backlog` and a `--json` mode — the resume read-contract lives in the CLI, not in prose parsing state internals. Test: `/clear` mid-sprint, re-invoke, land on the same stage. (Invariant 5) | 4 | M | ☑ |
| SK-013 | `/supskill run <sprint-id>` entry point: the init-or-resume-or-refuse matrix made explicit; the conductor never passes `--archive` itself; normalized-id comparison (case variants resume, never collide). Honours `sprint.entry` ∈ `SCOPE\|PLAN\|EXECUTE`. (**D7**) | 3 | M | ☑ |

## E3 — SCOPE + REFINE + Gate 1 (23 pts) — **the heart**

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-020 | SCOPE stage: dispatch `pm-execution:sprint-plan` as a subagent; write the sprint doc; record the artifact path. `sprint-plan` has **no output-path convention** — supskill supplies `<backlog-dir>/sprint-<normalized-id>-<slug>.md` as the dispatch default; `artifacts.sprint_doc` stays the only authority. Grown at S3 DoR: `init` refuses SCOPE entry without `--backlog`; `advance --to REFINE` requires a recorded, existing `sprint_doc` (`transitions.py` previously had no REFINE branch). | 4 | M | ☑ |
| SK-021 | REFINE stage agent: read the **live source**, cite `file:line`, surface gaps the backlog's one-liner could not know, grow the scope. Output is spec-shaped enough for `writing-plans`. (F-1) | 8 | M | ☑ |
| SK-022 | Proof-seam classification per story (`seam:`, `impact:`) → `provable: offline \| operator`. **E5 cannot drain-then-halt without this.** S3 DoR: the grammar and its parser (`proofs.py`) land in E3 so the format is fixed before E4 parses it; SK-033 only adds the state-loading verb (its points unchanged). | 5 | M | ☑ |
| SK-023 | Gate 1 in the conductor via real `AskUserQuestion`; decision + verbatim response → `gates.jsonl`. | 3 | M | ☑ |
| SK-024 | Citation audit: `scripts/supskill-audit` verifies every backtick-wrapped `file:line` citation in a sprint doc resolves against the working tree; the conductor runs it before Gate 1. The mechanical floor under F-5 — it proves citations *resolve*, not that claims are true. PAR at REFINE deferred with a named revisit trigger: if S3's demo shows a shallow refinement passing both the audit and the operator, E6's PAR story extends to REFINE. (New at S3 DoR, finding 4.) | 3 | M | ☑ |

**Risk:** SK-021 is the story most likely to underdeliver — "read the source and find the gaps" is
exactly the kind of task an agent will do shallowly and report confidently (F-5). Consider PAR here
too, not just at E6.

## E4 — PLAN + Gate 2 (14 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-030 | PLAN stage: dispatch `superpowers:writing-plans` with the refined sprint doc as the spec. S4 DoR: the conductor supplies the output path (`writing-plans`' own convention is dated and not derivable from a doc it has not read); the plan's citations are audited before Gate 2; the stage is resume-idempotent; and every plan task heading must name the story it serves — the join key E5 maps SDD statuses through. | 4 | M | ☑ |
| SK-031 | Intercept `writing-plans`' Execution Handoff. S4 DoR corrected this: it does **not** merely end by asking — each branch names a REQUIRED SUB-SKILL, so a headless plan agent can execute the entire sprint inside the PLAN stage, bypassing `advance --to EXECUTE`'s `G2_plan` precondition entirely while `state.json` still reads `PLAN`. Resolution, two layers: the template pre-answers *subagent-driven, always* and forbids both execution sub-skills (lint-asserted), and a HEAD-moved guard stops the run if the agent committed. The guard catches a committing agent, not an editing one — F-4's ceiling, stated. | 3 | M | ☑ |
| SK-032 | Gate 2 (plan review) → `gates.jsonl`. | 2 | M | ☑ |
| SK-033 | `supskill-state tasks --from <doc>` loads `tasks[]` (id, seam, provable, status=PENDING) from the refined sprint doc's proof lines — `proofs.py` stays the only parser. **Enforcement, not plumbing** (S4 DoR finding 2): `advance --to REVIEW` refuses while any task is non-terminal, which over an empty `tasks[]` passed vacuously — so a sprint could reach REVIEW having executed nothing. The verb also adds empty-list refusals on `→ EXECUTE` and `→ REVIEW`, plus load-time coverage validation joining plan task headings to story ids. (Proposed at S2 DoR, finding 6; grown at S4 DoR.) | 5 | M | ☑ |

## E5 — EXECUTE, drain-then-halt (23 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-040 | Dispatch `superpowers:subagent-driven-development` **from the conductor, which IS the SDD controller** — a subagent controller could neither record state (invariant 3) nor escalate to a human it does not have (D4). Every scratch artifact goes under the derived `sprint.scratch` via the `OUTFILE` override `task-brief` / `review-package` accept. S5 DoR: SDD's progress ledger has **no** override and is keyed by task number, reopening the D8 collision across sprints — so `state.json`'s `tasks[]` is the ledger and `progress.md` is never touched; **passing `OUTFILE` skips `sdd-workspace`**, the only thing that creates the scratch dir and git-ignores it, so the first `task-brief` dies on a missing parent and a target repo commits SDD's scratch; `BASE` is recorded before each dispatch (never `HEAD~1`); every dispatch names its model; the default-branch check stops the run before any dispatch; and **three** SKILL.md surfaces called EXECUTE a stub, including Gate 2's approval step — the only path that reaches the stage. | 7 | M | ☑ |
| SK-041 | **Drain-then-halt**: run every task that is neither `BLOCKED` nor downstream of a blocker; park the rest; then stop and escalate the batch. Target shape, not an error state. (**D4**) S5 DoR gave the row two definitions it never had: "downstream of a blocker" is **discovered, not predicted** — `Task` has no dependency edge (`model.py:75-80`), so a same-root-cause block is `PARKED` rather than double-blocked, at a cost of at most one wasted dispatch and with no schema change; and `provable` is a filter on **claims**, not on which tasks run. It also absorbs SDD's remaining human-decision points — the pre-flight conflict scan, a plan-mandated review finding, and a reviewer's "cannot verify from diff" item — as blockers or in-loop resolutions, never as guesses. | 8 | M | ☑ |
| SK-042 | Blocker records carry `options[]` + `recommend`. blinkebot's real S9a blocker is the fixture: the *recommended* option was wrong and option (c) was right — a bare "blocked" would have misled the operator. S5 DoR re-pointed this **down**: every structural rule shipped in S1 (`commands.py:228-253` — two-option floor, labelled options, a `recommend` that must reference one, a task that must exist). What remains is the conductor's authoring discipline and the fixture assertion that a wrong recommendation still leaves (c) reachable. Points moved to where the risk actually is (SK-043). | 2 | M | ☑ |
| SK-043 | Map SDD's `DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT` onto task status. `DONE_WITH_CONCERNS` proceeds but carries the concern to Gate 3. (**D5**) The join is the `SK-0xx` id in each plan task's heading, established by SK-030 and validated by SK-033: E5 adds no parser. **S5 DoR: the mapping was never the missing half — the VERB was.** No subcommand could write `DONE`, `DONE_WITH_CONCERNS` or `PARKED` (`cli.py:21-28`), so `advance --to REVIEW` (`transitions.py:39-46`) was unsatisfiable for any task that succeeded and no sprint could ever end. The story now carries `task --id … --status … [--note]`, its append-only `runs/<id>/tasks.jsonl` trail, its four refusals (unknown id, `NEEDS_CONTEXT`, `BLOCKED`, a note-less `DONE_WITH_CONCERNS`), and the multi-plan-task → one-story rollup rule. | 6 | M | ☑ |

## E6 — REVIEW (PAR) + Gate 3 + replan shapes (27 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-050 | **PAR**: two reviewer subagents on identical input, competitive frame ("false positives are worse than misses"), fixed aggregation — both agree → high confidence; one only → still actionable; **severity disagreement → always take the worse, no negotiation.** (**D9**, F-5) S6 DoR: no verb wrote a review finding (`cli.py:21-30` had no `review`) and PAR needed a genuinely new prompt template — unlike EXECUTE, which composes SDD's verbatim and adds none of its own. The story now carries the `review` verb (`Critical\|Important\|Minor` severity, `high\|actionable` confidence, append-only `runs/<id>/review.jsonl`, no schema bump), `scripts/supskill_state/review.py`'s pure aggregation function, and `skills/supskill/references/review-prompt.md`, dispatched twice with no cross-visibility. | 11 | M | ☑ |
| SK-051 | Gate 3: present batched blockers + review findings as **one** high-information decision. S6 DoR: `GATE_DECISIONS` was `("approved", "rejected")` and refused `replan` outright — S1 flagged this exact gap as deliberately deferred to E6 (`sprint-01-state-spine.md:104`). The story now carries the additive `GATE_DECISIONS` extension and the `references/gate.md` extraction sprint-04 named as E6's trigger (`sprint-04-plan-gate2.md:67`). | 4 | M | ☑ |
| SK-052 | The four replan shapes, incl. **generative writeback** — a review may append new `pending` rows to `backlog.md`. This is how blinkebot's S9 became S9a. | 8 | M | ☑ |
| SK-053 | **Refuse** to perform a north-star supersede autonomously. Operator-only, full stop. (Invariant 7) | 2 | M | ☑ |
| SK-054 | Propose the next sprint; stop. Do not roll on. (**D6**) | 2 | M | ☑ |
| SK-055 | Wire `review.py`'s `aggregate()`/`worse_severity()` into `record_review_finding` as an actual validation check, so a `--reviewer both --confidence actionable` or `--reviewer reviewer-a --confidence high` contradiction is refused at the recording boundary instead of accepted verbatim. (New at S6's own REVIEW/PAR dogfood, both reviewers independently, Important/high-confidence: `aggregate()`/`worse_severity()` have zero production callers today — PAR's "fixed rule, no negotiation" is enforced only by conductor prose, not by the function that implements it.) | 3 | S | ☑ |
| SK-056 | Give `replan_guard.py`'s `is_supersede()`/`refusal()` an actual runtime call site at Gate 3 (or fold their logic into the conductor prose path that already enforces invariant 7, and delete the dead module if a real call site isn't warranted). (New at S6's own REVIEW/PAR dogfood, both reviewers independently, Important/high-confidence: the module presents as Gate 3's north-star-supersede guard but is reached only by its own test file — `cli.py:191`'s only `refusal()` call is the older, unrelated `plan_guard.refusal`.) | 3 | S | ☑ |

## E7 — Packaging & distribution (9 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-060 | `marketplace.json` + first publish. **The plugin slug is immutable** — decide the name before this ships. | 3 | S | ☑ |
| SK-061 | `skill-creator` eval loop: should-trigger / should-not-trigger hit rate on the description. | 3 | S | ☑ |
| SK-062 | README + the build-in-public writeup for `bessavagner-page`. The lede is the finding, not the plugin: *"delegated agents cannot ask you anything — and in headless they silently receive an empty answer."* | 3 | C | ☑ |

## E8 — Validation (10 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-070 | Fixture repo + toy two-sprint backlog; end-to-end run. Needs real LLM calls — manual and gated, not in the default suite. | 5 | M | ☑ |
| SK-071 | **Drive blinkebot S11 for real.** If it cannot run one sprint the operator would have run anyway, it does not ship. | 5 | M | ☑ |

**Closed on three reports, not one.** `fixture-run-2026-07-19` cleared SK-070. SK-071 took
two runs to close honestly: `blinkebot-s17-2026-07-20` proved every mechanism against a
project the operator depends on, but that sprint never reached Gate 3, never merged, and its
feature shipped through a non-supskill path — a pass with a caveat, not a pass.
`playset-s1-2026-07-22` closed the loop: a real greenfield project driven from three tracked
files and no code, through all five stages and all three gates, to merged code on `main`
with 165 tests green. Its PAR pass caught a Critical defect that had already survived 165
passing tests, two rounds of task review and a nine-task drain, then routed it into that
project's backlog as scheduled work. That report also carries eight findings against
supskill itself, three of which no fixture repo could have produced — see
`validation/reports/` (gitignored; point-in-time run records, not tracked source).

---

## E9 — Findings from real runs (70 pts)

Written back from the E8 reports (`validation/reports/`, gitignored) and, from SK-114 on,
mined from the on-disk `.supskill/runs/` trails of projects that adopted supskill after E8
closed — so the punch list they produce lives in git rather than in point-in-time run
records. Every row cites the run that surfaced it. These are defects and design gaps in shipped v1 code, not new
capability — E9 is the same principle E8 proved, turned on supskill itself: what a real run
finds is scheduled, not remembered.

**Already fixed, recorded for context, not scheduled:** the stage templates depended on a
dispatched subagent's final chat message, and about a third of dispatches returned a
placeholder while having done the work — at REVIEW a lost review read as a clean diff. Fixed
in `7dfb0f9` (v0.2.1): every dispatch writes its deliverable to a conductor-derived path and
the conductor reads the file, never the reply. The playset s2 run confirmed it held at the
stage that failed in s1. This row exists so the fix is not re-litigated; it needs no work.

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-100 | **Collapse SCOPE and REFINE; drop the `pm-execution:sprint-plan` dispatch and the fabricated capacity model.** SCOPE dispatches `sprint-plan` (`scope-prompt.md:34`) whose two core outputs are both null here: story selection is already the backlog's job (recommended order + first-unchecked epic), and capacity is a hard-coded constant the template invents — "working capacity ~34 pts, ~18% buffer, ~28 committable" (`scope-prompt.md:36-37`) — with no team, velocity, or history behind it. SCOPE's output is never gated (Gate 1 is on the *refined* doc), so it produces an ungated intermediate REFINE substantially rewrites anyway, at 50–119k tokens per run (playset s1/s2). REFINE is the load-bearing stage and stays. Fold the two into one stage that seeds the sprint doc from the epic's backlog rows and reads live source in one pass; drop the `pm-execution` dependency, shrinking the cross-marketplace install surface to one plugin. Keep both gates and the PLAN dispatch untouched. **Anchor of this epic — plan it first.** (playset s1/s2; capacity finding independently reached by a second, non-supskill session.) | 8 | M | ☑ |
| SK-101 | **Finish the story-id-prefix feature.** The parsers honor the configured prefix (`plan_coverage.py:31,78`, `proofs.py`) but the prompt templates still hard-code `SK-0xx` (`scope-prompt.md:41`, `plan-prompt.md:46`, `replan-shapes.md:23`), and `supskill-audit --proofs` passes vacuously on a prefix mismatch rather than refusing. On the playset run (`PLS` prefix) only the REFINE agent noticing by judgment kept the run alive; the mechanical net did not catch it. Templates parameterize on the prefix; the audit refuses a doc whose story ids do not match the configured prefix. The one shipped half-feature that bit two of three validation targets. | 5 | M | ☑ |
| SK-102 | A blocker silently cancels its story's unrun plan headings. When one story spans several plan task headings, blocking it mid-way parks the remaining headings without a record an operator would see. Discovered structurally, not triggered (playset plans happened not to hit it). Make the cancellation observable — the parked headings and the blocker that parked them land in the trail Gate 3 reads. | 3 | M | ☑ |
| SK-103 | Give `block` an inverse. After both s1 blockers were resolved, `show --json` still reported "open blockers: 2" and Gate 3 presented two settled decisions as live ones — the operator reconstructs resolution from the tasks trail. A blocker whose task reached a terminal non-blocked status should read as resolved. (playset s1.) | 3 | M | ☑ |
| SK-104 | Detect a stale `review-final.diff` between EXECUTE and REVIEW. On s1, out-of-band commits landed after the halt and the recorded review package no longer matched the branch; the conductor caught it by judgment and regenerated. Make the staleness detectable mechanically — REVIEW refuses or regenerates when HEAD has moved past the package's recorded base. (playset s1.) | 3 | M | ☑ |
| SK-105 | Dispatch scratch hygiene: a fix subagent ran `git add -A` and swept `.omc/` harness state into a commit; the controller caught it and reset. A dispatched subagent must not be able to stage the whole working tree — scope its commits to its declared files, or guard foreign state at the dispatch boundary. (playset s1.) | 3 | M | ☑ |
| SK-106 | Runtime preflight that the dispatched skills resolve. If a dependency is missing, disabled, or its marketplace unreachable, a stage dispatches a skill that does not exist and the stage improvises — the exact failure the project exists to prevent. Refuse at run start when a required skill is unresolvable, the way playset's own PLS-040 refuses on a missing binary. (both runs, by construction.) | 3 | M | ☑ |
| SK-107 | Guard against `writing-plans` laundering a false proof. On s1 the plan ran its own code in a scratch project, got 127 green, and its self-review mapped an acceptance criterion to a test — while the shipped `derive_path` was not injective and the "green" suite never checked collisions. The PLAN template should ask for verified *mechanisms* and interfaces, and withhold implementation bodies, so EXECUTE's reviewer independence reviews reasoned code rather than transcribed code. (playset s1; not reproduced s2; **s5 reproduced it in a new shape** — the plan mandated verbatim httpx `ASGITransport` streaming tests that hang against the pinned `httpx 0.28.1`, a test *transport* it specified but never verified would run; the implementer correctly blocked, but the plan had asserted an unrunnable proof harness. Two instances now → re-pointed C→M, and narrowed: a novel test harness/transport must be proven runnable in the plan, not merely described.) | 3 | M | ☐ |
| SK-108 | Decide what append-only writeback means, and enforce it. The generative-writeback shape is append-only by prose, not mechanism: s1's writeback made 0 deletions and left the summary total stale; s2's made 3 deletions to correct the total. Same conductor, same shape, opposite call. Either enforce strict append-only and treat the roll-up total as a permitted exception, or enforce it in code — but not leave it to per-run interpretation. (playset s1 vs s2 — the finding a fixture repo could not produce.) **Third instance (ledgerus s6): strictly append-only — 63 insertions, 0 deletions, one hunk — and the conductor declined to tick two boxes an earlier sprint had closed, documenting the restraint in the written section instead of acting on it. Three runs, three readings: s1 (0 deletions, stale total), s2 (3 deletions, total corrected), s6 (0 deletions, restraint recorded). s6 is the cleanest instance and argues for strict append-only with the roll-up total as a named exception. That is enough evidence to decide this row rather than carry it. **Fourth instance (ledgerus s8): 120 insertions, 6 deletions, and the deletions are confined to the Status block that still named s8 as next — no row's points or status touched. So the exception set has two members, not one: the roll-up total *and* the Status block. Both are derived summaries rather than backlog rows, which is the distinction to encode — append-only binds rows; a derived header is rewritten, because leaving it stale is the failure, not the edit.** | 2 | S | ☐ |
| SK-109 | Measure teammate-dispatch token cost instead of guessing it. The `7dfb0f9` fix delivers *findings* by file but PAR reviewers run as mailbox teammates whose transcripts the conductor cannot retrieve, so it recorded each at an estimated 70k — the ledger now silently mixes measured and estimated rows with no marker. Either dispatch reviewers as trackable tasks, or mark estimated cost rows as estimates. (playset s2; s3 corroborated — s3's REVIEW rows came back measured, `63,016·11` / `61,307·11`, but 0.3.0 changed no accounting code, so that was operational luck, not a fix. The estimated/measured ambiguity is still unmarked.) | 2 | C | ☑ |
| SK-110 | The collapsed SCOPE stage still logs its cost under the pre-collapse label `refine`. After SK-100 folded REFINE into SCOPE, the conductor still runs `cost --stage SCOPE --label refine` (`SKILL.md:128`, and `--label refine-retry` at `SKILL.md:136`), so `costs.jsonl` carries a `{"stage": "SCOPE", "label": "refine"}` row that reads as a contradiction — the one place the collapse left a seam showing. Nothing parses the label, so this is cosmetic: relabel it `scope` (or drop the label) so the ledger names the stage that actually ran. (playset s3 — first run under SK-100.) | 1 | C | ☐ |
| SK-111 | `supskill-state` refuses when run from a worktree cwd during EXECUTE. With EXECUTE isolated into `.worktrees/<id>`, the conductor ran `supskill-state cost` from the worktree cwd and was refused three times (`no state file at …/.worktrees/s5/.supskill/state.json`), recovering by `cd`-ing to the repo root each time. `store.state_path` resolves `.supskill/` from cwd with **no** upward search (`store.py:24-30`, by design), so the refusal is correct but the friction is systemic whenever the dispatch root ≠ the state root. Either make the worktree notes require every state call to `cd` to the original repo root first, or have `supskill-state` resolve `.supskill/` from the main worktree's root when cwd is a registered linked worktree. (playset s5.) | 2 | M | ☑ |
| SK-112 | The EXECUTE task-reviewer's findings arrive as a placeholder reply. SDD's task-reviewer prompt, composed verbatim by EXECUTE, returns its findings as its final chat message; on s5 that collapsed to `Done.`/`.` on both task reviews, and the conductor had to resume the agent and persist to a file to recover them. supskill already closed this for its **own** dispatches (`7dfb0f9`: `references/review-prompt.md`'s `FINDINGS_PATH`, "read it back … nothing parses your reply"), but EXECUTE inherits SDD's prompt, which has no file handoff. Wrap the EXECUTE task-review dispatch so the reviewer writes findings to `<scratch>/review-findings-<N>.md` and returns only a status line — supskill owns the dispatch wrapper even though the prompt body is SDD's. (playset s5.) | 3 | M | ☑ |
| SK-113 | The halt prose misleads on what "non-terminal" means at `advance --to REVIEW`. On s5 the conductor expected the advance to refuse with an open blocker, then rationalized when it succeeded. The behavior is correct — `TERMINAL_STATUSES` includes `BLOCKED` and `PARKED` (`transitions.py:37-45`), so a blocked sprint advances to REVIEW carrying the blocker to Gate 3 — but the SKILL.md halt prose reads as though any open blocker blocks the advance. One line naming `BLOCKED`/`PARKED` as terminal resting states that reach REVIEW removes the stumble. (playset s5.) | 1 | C | ☐ |
| SK-114 | **`replan-guard` passes a generative writeback that has no recorded backlog to write to.** `init` requires `--backlog` only at SCOPE entry (`commands.py:60`), so an `--entry EXECUTE` sprint carries `backlog: null` to Gate 3 — and `replan-guard --shape generative-writeback` returns exit 0 anyway, validating the *shape* while never checking the *target* exists (`cli.py:224-242` passes only `--shape`; the module reads no state). On ledgerus s6 the conductor then appended 63 lines to `docs/sprints/backlog-01/backlog.md`, a path `state.json` never authorized, inferred from `artifacts.sprint_doc`'s parent directory. It inferred correctly and the writeback was clean — which is the problem: the run was carried by the agent's judgment while the mechanical net passed vacuously, the same shape as SK-101. Contradicts SCOPE's own rule that "the recorded artifact is the only authority anything downstream reads". Give `replan-guard` the state and refuse the three amending shapes when `state.backlog` is null. Also: the step-3 refusal template (`SKILL.md:74-79`) drops the operator's `--backlog`/`--branch`/`--slug` from the command it tells them to run — the conductor re-added it by judgment. Same root: the target is deduced, never authorized. (ledgerus s6; the predicted hard failure did **not** occur, which is what makes it worth a row.) | 3 | M | ☑ |
| SK-115 | **Abandoning a sprint at REVIEW discards the decision that mattered most.** ledgerus s5 halted correctly — SK-052 blocked on a genuine `AGENTS.md` self-contradiction, SK-053/054/055 parked as downstream of that one root cause, all four terminal, advanced to REVIEW. The operator then resolved the contradiction out of band and re-inited s6 at `--entry EXECUTE`. `runs/s5/archive-1/gates.jsonl` holds G1 and G2 and no G3, so **how** that blocker was decided exists nowhere on disk: the trail preserves the question and loses the answer. This is the append-only audit trail failing at the one point it was built for. Distinct from SK-103 (a settled blocker still reading as open); here no decision is ever recorded at all. `init --archive` over a sprint resting at REVIEW with `G3_review: null` should refuse, or record an explicit superseded/abandoned decision naming the sprint that took over. (ledgerus s5→s6.) | 2 | M | ☑ |
| SK-116 | An EXECUTE-entry continuation silently inherits the previous sprint's artifact pointers. ledgerus s6 carries `sprint.id: s6` with `artifacts.sprint_doc: docs/sprints/backlog-01/sprint-s5.md`, `dev_plan: …/2026-07-23-sprint-s5.md`, and `branch: s5` — it ran no SCOPE and no PLAN, then spent 2.78M tokens (the largest EXECUTE on record across both validation targets) against a plan written for a different sprint id. The run was correct and the resumption path did its job; the defect is that state cannot distinguish "s6 continues s5" from "s6 has its own doc that happens to be misnamed", so the cost ledger and the artifact pointers disagree about which sprint they describe. Record the continuation explicitly — a `continues` field set by `init --entry EXECUTE`, or carry the source sprint id forward — so the trail says what the sprint actually was. (ledgerus s6.) | 2 | C | ☑ |
| SK-117 | The sprint doc and dev plan a branch implements are never staged. SCOPE and PLAN derive their output paths, write the files and record them as artifacts, but nothing stages them and no stage tells the operator to — so the two documents that authorize a sprint sit untracked while the code they authorize is committed. playset's reviewers raised it at s1 and again at s2 ("the plan a branch implements is not in the branch"); ledgerus needed a hand commit (`a3433df` there) after s6. Three occurrences, two projects, twice surfaced by a reviewer rather than a mechanism. **Report, do not stage:** supskill never runs git on the operator's behalf — it will not create, switch or delete a branch — so an automatic `git add` breaks the posture the EXECUTE branch check already states. A Gate 3 check that names any recorded artifact untracked by git fits the guard-module shape and leaves the commit to the operator. (playset s1/s2, ledgerus s6.) | 2 | M | ☑ |
| SK-118 | `_archive_existing` archives `state.json` and `gates.jsonl` into `runs/<id>/archive-N/` on `init --archive`, but leaves `runs/<id>/package.jsonl`, `tasks.jsonl` and `blockers.jsonl` where they are — so every trail the SK-102/103/104 group reads outlives the run that wrote it, while `gates.jsonl` (read by `_last_gate_responses`) is the one trail that actually gets archived. Reusing a sprint id across `init --archive` therefore lets a previous run's package record survive under the new run's id: `review-guard`'s Critical false pass (final review of `feat/e9-gate3-inputs`, 2026-07-26) was mitigated there by refusing when the recorded diff is not on disk, but a diff that happens to still exist at the same derived scratch path (`derive_scratch` is a pure function of the sprint id) walks past that check. The same asymmetry lets `derived.blockers.*.plan_headings` and `render_show`'s `resolved by`/note report a *previous* run's facts as though they were this run's — worse than the absence SK-102/SK-103 were filed to fix, because a stale value reads as known. Move the whole `runs/<id>/*.jsonl` set into `archive-N/`, the way `_archive_existing` already does for `gates.jsonl`, so a reused id starts every trail empty, not just two of five. (final review of `feat/e9-gate3-inputs`, 2026-07-26.) | 3 | M | ☐ |
| SK-119 | Two residuals parked at the `feat/e9-gate3-inputs` merge, both in the shape this epic exists to remove: a check that reads as coverage without providing it. (a) `tests/test_blockers_resolved.py:153`'s `test_a_non_resolving_note_on_an_open_blockers_task_does_not_leak_in` **would pass with the guard it pins removed** — its own scenario makes that guard structurally unreachable, so the test asserts nothing about the behaviour it names. The guard is correct by inspection; the test is not evidence of it. (b) `cli.py:355`'s `(dispatch_root / str(record.get("path", ""))).exists()` silently **passes** rather than refuses on three malformed recorded paths — empty (`Path(root) / "" == Path(root)`, which always exists), absolute (bypasses `dispatch_root` entirely per Python's `/` semantics), and `..`-bearing (walks outside `dispatch_root`). None is reachable through a documented workflow, because `record_package` is the sole writer and already refuses an empty `--path`; all three need a hand-edited trail. It is the same trust-the-trail posture the module already takes at `record.get("head", "")`, inherited rather than introduced — but a guard that silently passes on malformed input is the exact failure mode `review-guard` was built to end. Fix (a) by making the test fail without its guard; decide (b) deliberately — either validate the recorded path at read time or state the trust boundary in the docstring. (final review + fix-wave re-review of `feat/e9-gate3-inputs`, 2026-07-26; adjudicated as non-blocking at merge, filed rather than remembered.) | 2 | C | ☐ |
| SK-120 | **Nothing in a run's trail records which supskill produced it.** ledgerus s8 was drained and reviewed under **v0.5.0** (marketplace clone `6fcf932`, 2026-07-24) while `main` here sat 33 commits ahead — so `review-guard` never ran at REVIEW (`runs/s8/` has no `package.jsonl`; the `package` verb did not exist), `artifact-guard` never ran before Gate 3, and the two REVIEW cost rows carry no `estimated` key at all because 0.5.0's `record_cost` does not write one. None of that is legible from `.supskill/`: establishing it took a diff of the installed clone against this repo. This epic is *defined* as findings mined from on-disk run trails, and those trails cannot state which code wrote them — so a row re-filed from an old run may already be fixed, and a fix credited to a run may never have been installed when it ran. Stamp the plugin version into `state.json` at `init` and name it in the run checklist's step-4 resume report, so a trail carries its own provenance. (ledgerus s8; the skew was six days old — SK-102/103/104/109 merged 2026-07-26, s8's REVIEW ran 2026-08-01.) | 2 | M | ☐ |
| SK-121 | **`cost` cannot say "unknown", so the conductor said zero.** SK-109 shipped `--estimated`, and `review-notes.md` mandates it for a mailbox teammate — "its token count is your estimate and the row must carry `--estimated`". The s8 conductor declined to invent a figure it could not measure and filed `--tokens 0` instead, disclosing the choice in its halt report. That is the right instinct meeting a verb with no representation for it: under current `main` the same choice writes `{"tokens": 0, "estimated": false}` — a measured-looking zero, strictly worse than the unmarked estimate SK-109 was filed against, because 0 is a number and `estimated: false` is now a false assertion rather than an absent field. Let `cost` record an absent count (null tokens), or let `--estimated` stand without a figure. **Both readings are now on record, from the same harness two runs apart: ledgerus s8 filed `tokens=0` and disclosed the refusal to guess; ledgerus s9, the first run under 0.6.0, filed `110000`/`105000` with `estimated: true`. Same missing information, opposite calls — the ledger now carries a zero and a guess side by side, and neither conductor was wrong under the prose it was given. That is the same per-run-interpretation shape as SK-108, and it is what decides this row: the verb needs a representation for "unknown" rather than a convention for it.** (ledgerus s8 and s9; SK-109's second-order effect, visible only once the marker existed.) | 1 | C | ☐ |
| SK-122 | **The drain's only oracle is a local gate; CI is never consulted.** Across s8's twelve tasks every task reviewer certified "gate green" against a locally-run suite, and the project's `main` was red the whole time: SK-087's import-order regression test passes only where an untracked `.env` exists, because `subprocess.run(env={...})` replaces the child environment and discards CI's job-level `DATABASE_URL` (ledgerus CI run 30195478228, 1 failed / 143 passed, red since 2026-07-26). Twelve green certifications, six days, one red build — and PAR found it only because a reviewer went looking outside the diff. Nothing in EXECUTE's cycle or REVIEW's PAR reads the branch's CI status, so "the gate is green" means "green on this machine" and no stage says so. Either the halt report claims only what a local run proves — the `provable` distinction, extended from the seam to the environment — or EXECUTE surfaces the branch's CI conclusion where it already surfaces the gate. (ledgerus s8 — the run's most consequential finding, and invisible to every mechanism supskill currently has.) | 3 | M | ☐ |
| SK-123 | **A proof line names a mechanism nobody checked is live.** ledgerus SK-084 was scoped, planned, implemented and task-reviewed as an HTMX error-path fix; htmx is loaded nowhere in that project — no `<script>` in any template, no `static/` — so every `hx-*` attribute is inert and the "fix" replaced a re-rendered form with a headless fragment the user cannot retry from. Each layer was locally correct: SDD's task reviewer reviews the **diff**, so "does the mechanism this diff targets exist?" is out of scope by construction, and `supskill-audit --proofs` validates a proof line's citation *shape*, never that what it cites is wired up. The stage that could have caught it is SCOPE, whose whole claim is refinement against live source (SK-100). Extend that pass to the mechanism a proof line depends on, not just the `file:line` it points at. (ledgerus s8; caught at PAR by one reviewer of two — the strongest evidence yet for the competitive frame, and another instance of the mechanical net passing while judgment carried the run, the shape SK-101 and SK-114 also name.) | 3 | M | ☐ |
| SK-124 | **Two reviewers can contradict each other on fact, and the aggregation table has no row for it.** `review-notes.md`'s table resolves *severity* disagreement (worse wins) and leaves matching to judgment, but on s8's SK-089 finding the two reviewers reached opposite conclusions about the same artifact — whether the new test's oracle survives reverting the production fix it is supposed to pin. The conductor recorded it as `reviewer-a`/`actionable` with the word `DISPUTED:` written inside the `--finding` prose and asked the operator to adjudicate. Sound improvisation, and entirely invisible to anything reading `review.jsonl`: no field says two reviewers disagreed, so a contradiction is indistinguishable from a single-reviewer observation at Gate 3 — the one screen where it most needs to be legible. Give the aggregation table a contradiction row and the `review` verb a way to record one. (ledgerus s8.) | 2 | C | ☐ |
| SK-125 | **The plan/story join reads every story id in a heading, not the join key.** `plan_coverage.py:89` runs `findall` over the whole `### Task N` line, while the module's own docstring (`:8-9`) declares the contract as the trailing parenthetical `(SK-0xx)`. Implementation and stated contract disagree, in both directions. **Loud direction:** a heading whose prose names a historical id refuses a correct plan — ledgerus s9's PLAN was refused on `### Task 4: Delete SK-089's dead hidden inputs (SK-096)` and `### Task 6: Close the import-linter hole SK-087 opened (SK-099)`, where s8's `SK-089`/`SK-087` are prose and the join keys `SK-096`/`SK-099` are correct; all 14 stories were in fact covered. **Silent direction, the dangerous one:** when the prose id *is* in the sprint doc, `named.add(story)` (`:96`) marks it covered, so the "plan drops this story" check (`:100-102`) passes vacuously — the single guarantee SK-033 built this module to provide. EXECUTE then records a status against each story the heading names, so a task is marked `DONE` against work it never did, and `headings_for_story` (SK-102) reports headings that do not serve the blocked story. A PAR-drain sprint is exactly where this fires: headings naturally cite the story that caused the finding. Anchor the parse on the trailing `(...)` group the docstring already specifies, and keep the multi-story form (`(SK-041, SK-043)`) the drain depends on. (ledgerus s9 PLAN, 2026-08-03 — refused a correct plan on a live run; the silent direction found by inspection alongside it.) | 3 | M | ☐ |

**Sequencing.** SK-100 is the anchor and is planned first — it is a design change the rest
sit downstream of, and it removes SK-108's capacity surface as a side effect. SK-101 is the
only High: it is a shipped half-feature and gates any non-`SK` project. The rest are M/C and
independent of each other. SK-111 through SK-113 were filed from the playset s5 run (E3, an
HTTP-API sprint); s5 also corroborated SK-107, which is re-pointed C→M. SK-114 through
SK-116 were filed from the ledgerus runs (a brownfield Django app, joined at s3) — the first
non-playset evidence in this epic. SK-114 is the only row here that blocks a run already in
progress: ledgerus s6 is at REVIEW with a null backlog now.

**Delivered 2026-07-24 (SK-114..117).** Two divergences from the rows as filed, recorded
here rather than by editing them: SK-115 asked for "refuse, or record an explicit
superseded/abandoned decision" — the refusal was chosen, so `gate --decision` keeps its
three values and the schema is unchanged. SK-117 asked for "a Gate 3 check"; it shipped as
the `artifact-guard` verb the conductor runs before Gate 3's question, which is the same
check at the same point, under a name the row does not use.

**Delivered 2026-07-26 (SK-102, SK-103, SK-104, SK-109).** The Gate-3 input group: the
highest-stakes screen in the product was assembled from four partly-untrustworthy inputs,
and each is now either derived, recorded, or refused. Six divergences from the rows as
filed, recorded here rather than by editing them. SK-103 asked for "a terminal non-blocked
status" to resolve a blocker; `PARKED` is terminal and does **not** resolve one — a parked
task never ran, which is the opposite of settled, so the resolving set is `DONE` and
`DONE_WITH_CONCERNS`. SK-103 also asked to "give `block` an inverse"; it shipped as a
derivation with no new verb, because `task --status DONE --note` already records how a
blocker was settled and a second mover could disagree with it. SK-102 asked for "the parked
headings"; what is recorded is every plan heading serving the blocked story, because the
spine tracks stories and nothing in it knows where a drain stopped — the narrower claim
would have been fabricated. SK-109 took the second of its two options (mark estimates)
rather than the first (make reviewer dispatches trackable), which remains open as a
possibility and is not filed as a row. SK-104 asked only that REVIEW detect a stale
package; what shipped is that **plus** a `--dispatch-root` on the `package` verb, because
the row's implied design was wrong: the guard originally rev-parsed the *state* root, while
the package is cut at the *dispatch* root — and `SKILL.md`'s EXECUTE stage isolates into a
worktree when the sprint starts on the default branch, making those different repos with
different HEADs. `store.resolve_root` deliberately returns the main worktree root from a
linked-worktree cwd (that was SK-111), so the guard could only ever refuse in the worktree
workflow, and its own refusal text told the operator to do something that could not clear
it. The fix: the package record carries where it was cut, and the guard rev-parses that. A
`--dispatch-root` flag on the guard itself was considered and rejected as repeating
SK-114's "deduced, never authorized" shape. SK-104 as filed also says the guard should
fire "when HEAD has moved past the package's recorded **base**"; what shipped compares
the recorded **head** instead. The shipped choice is correct — PAR reviews the diff
between base and head, and it is head that moves out from under a cut package — and the
plan's own Self-Review names the resulting ceiling (a package cut at the right head from
the wrong base walks past the guard), but the note enumerates its divergences by name and
this is the sixth.

**Filed 2026-08-03 (SK-120..SK-124), from ledgerus s8 — and read this before mining that run
again.** s8 ran under **v0.5.0**, the last release cut, while `main` here sat 33 commits and two
delivered waves ahead: SK-114..117 (2026-07-24) and SK-102/103/104/109 (2026-07-26) were merged
and unreleased when s8 was drained on 2026-07-25 and reviewed on 2026-08-01. So s8 is **no
evidence at all** about those eight rows — `review-guard`, `artifact-guard`, the `package` verb
and `--estimated` were not installed and could not have run. Anything s8 appears to say about
them is an artifact of the skew, not a regression, and SK-120 exists so the next reader does not
have to diff the marketplace clone to learn that. What s8 *is* evidence for is the five rows
above and a fourth instance of SK-108. Two of the five (SK-122, SK-123) are the run's real
yield: both Criticals PAR found are classes of defect no supskill mechanism can currently see —
one because the only oracle is a local test run, one because a diff-scoped review cannot notice
an absent mechanism. Neither was caught by the twelve task reviews that certified the work
`DONE`; both were caught at PAR, one of them by a single reviewer of two, which is the
strongest evidence the competitive frame has yet produced (F-5).

## E10 — The operator decides, the conductor acts (30 pts)

Design: [`docs/superpowers/specs/2026-08-04-operator-interaction-model-design.md`](../../../superpowers/specs/2026-08-04-operator-interaction-model-design.md).

Every seam where supskill touches the operator today hands back a command to type.
None of them needs the operator's hands — no elevated privilege, no knowledge the
conductor lacks, no judgment it has not already made and recommended. They need the
operator's *decision*. This epic separates the two: the decision stays human and
recorded, the typing moves to the conductor. Filed from ledgerus s8/s9, where
starting a sprint took two invocations, the sprint doc and dev plan stayed untracked
until `artifact-guard` refused at Gate 3, and the Shape-1 writeback was left
uncommitted by design.

**Scope, settled before design.** State verbs plus `git add`/`git commit`. **Not**
merge, **not** push, **not** model invocation — `disable-model-invocation: true`
stays and E7's tension (`references/invocation-model.md`) stays open. Everything in
scope is local and reversible: a wrong commit is a `git reset`, never something
published. Only gates and blockers interrupt; everything else executes and is
reported. Batch acceptance is allowed and marked.

**The constraint this epic must carry.** F-4 says the script cannot prove a human
answered a gate, and D4 records that `AskUserQuestion` auto-resolves **empty in
~37ms** headless. Today the friction *is* the consent signal, because typing cannot
auto-resolve. Today an empty answer costs a missing record; here it would cost an
executed action nobody chose. SK-136 is that rule, and it is the weakest row in the
epic — a precondition, not a mechanism.

Numbering starts at SK-130 rather than SK-126: E9 is explicitly expected to keep
growing, and interleaving two open epics in one id range makes the trail harder to
read than a gap does.

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-130 | **Classify every stop as remediable or evidential, and pin it with a test.** Each stop the CLI can produce gets exactly one recorded label. *Remediable* (conductor acts): the id-mismatch refusal when the on-disk sprint's G3 **is** recorded; `artifact-guard`; a Shape-1 writeback this run just applied. *Evidential* (still refuses, relayed verbatim): `review-guard` — SK-104's point is that a regenerated package comes back *clean*, so the refusal **is** the finding; `plan-guard` — the plan agent committed, which is a misbehaving agent, not a fixable state; `commit-scope-guard`; `replan-guard --shape north-star-reset` (invariant 7); `preflight`; the `tasks` coverage refusal — a dropped story is a hole, not a chore; and `init --archive` over a sprint at REVIEW with no G3 (SK-115), where nothing can be remediated because no decision exists yet. `--archive` appearing in **both** tables, split on whether a decision exists to preserve, is the classification doing real work rather than restating a whitelist. **A test asserts every guard and refusal reachable from `cli.py` appears in the table exactly once** — without it this decays into per-run prose judgment, which is SK-108's failure mode across four runs and three contradictory readings. **Anchor of this epic — plan it first.** | 3 | M | ☑ |
| SK-131 | **`actions.jsonl`: a durable record of what the conductor did on the operator's behalf.** New append-only per-run trail with one entry per conductor-executed action — kind, reason, the exact command, resulting SHA where there is one, outcome — written by a new `action` verb that only the conductor calls, the same posture as `cost`. Not optional bookkeeping: the scope decision makes these actions silent, and **invariant 5** says the conductor is disposable with `.supskill/` as its only memory, so a report delivered in a conversation `/clear` destroys is not a record. This is what keeps "what did it do to my repo?" answerable from disk after the conversation is gone. | 3 | M | ☑ |
| SK-132 | **`decide` — give a blocker's answer a verb.** `decide --task SK-0xx --option "(a)" --response "<verbatim>"`, refusing an option label absent from that blocker's recorded `options[]` (reusing `_OPTION_LABEL`, `commands.py:411`), an empty `--response`, an unknown task, and a re-decide of a settled blocker — writing nothing on any refusal. `show` derives resolution from the decision instead of inferring it from task status. SK-103 deliberately shipped resolution as a derivation with no verb, reasoning that `task --status DONE --note` already records how a blocker was settled and "a second mover could disagree with it." That was right while the answer was free prose; it stops being right once the answer is a chosen option, because the chosen label is a recorded fact rather than an inference. SK-103's derivation stays as the fallback for blockers settled the old way. (ledgerus s9 settled three blockers whose trail records only `DONE`.) | 5 | M | ☑ |
| SK-133 | **`--batched` on `gate` and `decide`.** Exactly SK-109's shape and exactly its reason: a ledger that cannot distinguish two provenances is lying quietly. `show` renders it, so a batch-accepted G3 and an individually-reasoned one are tellable apart. Batching is offered **only when every item in the batch carries a recommendation** — a question with no recommended answer cannot be bulk-accepted. (ledgerus s9: the operator answered three blockers with one "go with your recommendations on all three", which the trail cannot distinguish from three considered calls.) | 2 | M | ☑ |
| SK-134 | **`commit-scope-guard` covers the conductor's own commits.** Today it guards an implementer's commits across a task's `BASE`..`HEAD` (SK-105, after a fix subagent swept `.omc/` into a commit). Every conductor-executed commit runs the same guard with the same refusal before it lands. The actor that gains the most reach under this epic must not be the one the guard exempts. | 3 | M | ☑ |
| SK-135 | **Rewrite the prose that tells the operator to type.** The run checklist's step-3 refusal template, the SCOPE backlog-null refusal, Gate 3's `artifact-guard` paragraph, and the Conventions line **"Never pass `--archive`"** all change to match SK-130's classification. `--archive` becomes: pass it only to close a sprint whose G3 decision is recorded, and record the action. Downstream of SK-130 — the prose describes the table, so the table lands first. | 3 | M | ☑ |
| SK-136 | **A run that cannot ask cannot act.** `record_gate` accepts an empty `--response` **by design** (`commands.py:402`: "empty is accepted and recorded by design (F-4)") so a fabricated approval leaves a readable empty quote in the trail; enforcing the empty-answer rule inside `gate` would destroy that mechanism. Enforce it one level up instead: before its first silent action of a run, the conductor establishes that an interactive operator exists, extending the run checklist's existing preflight step. A run that cannot raise a gate does not get to execute actions on the operator's behalf either. **Recorded as the weakest row in the epic**: it is a precondition backed by conductor discipline, not a mechanism that makes the failure impossible — F-4's ceiling restated one level out. | 2 | S | ☑ |
| SK-137 | `action --result` has no allow-list. `cli.py` documents `"ok \| failed"` in its help text but sets no `choices=`, and `record_action` never validates the value, so `--result banana` reaches `actions.jsonl` unchallenged. Only the conductor writes the field and nothing reads it yet, so a bad value is a cosmetic trail wart rather than a wrong action — which is why the E10 final review triaged it post-merge rather than blocking on it. Add `choices=["ok", "failed"]`, or a `StateError` guard mirroring the `--command` non-empty check. (E10 final review, 2026-08-04.) | 1 | C | ☐ |
| SK-138 | **One `Stop` id per verb, where several verbs have several distinct refusal branches.** `review-guard` has three (no package recorded, the recorded diff is missing from disk, HEAD moved past it) and `replan-guard` two (the supersede shape, the null-backlog target), but `STOPS` carries one id each. Verb-level totality is what `verbs_covered()` needs and condition-level ids would not have prevented any defect on the E10 branch, so this is a design question rather than a bug: decide whether a stop id names a *verb's* refusal or a *condition's*, and if the latter, what keeps the totality test checkable. (E10 final review, 2026-08-04.) | 2 | C | ☐ |
| SK-139 | `test_refuses_deciding_the_same_blocker_twice` does not assert the refusal wrote nothing, unlike every sibling refusal test in `tests/test_decide.py`, each of which follows its `pytest.raises` by re-reading the trail. The property does hold — the dedupe scan precedes `append_jsonl` — so this is a missing assertion, not a missing behaviour. It is the same shape as SK-119(a): a test that reads as coverage of a property it never checks. (E10 final review, 2026-08-04.) | 1 | C | ☐ |
| SK-140 | `gate.none` and `decide.none` carry byte-identical `condition` text ("records a decision") in `stop_classes.STOPS`, describing two different verbs. Purely cosmetic — `id` is what `test_stop_ids_are_unique` asserts and what `classify()` dispatches on, and `condition` is documentation — but a reader skimming the table by condition alone would conflate the two verbs. (E10 final review, 2026-08-04.) | 1 | C | ☐ |
| SK-141 | No test drives `_blocker_view`'s `decisions.get(...)` → `None` fallback through `render_show_json` — an open blocker with no `decide` call yet, asserting `decision: null` and `batched: false` come from the literal rather than a stored value. The E10 review filed this alongside an irony that its own I1 fix then removed: while `decide` had no caller, the fallback was the only branch that could execute in production. Now that Gate 3 instructs `decide`, both branches are live and the fallback is the untested one. (E10 final review, 2026-08-04; the stated rationale is recorded as superseded rather than repeated.) | 1 | C | ☐ |
| SK-142 | `references/stop-classes.md` documents the eleven non-`no_stop` stops (3 remediable, 8 evidential — the review said nine, before its own fix wave added two), and its framing line ("every seam where `supskill-state` stops carries exactly one class") can read as implying those nine are all there is. Thirteen further verbs are classified `no_stop` in `stop_classes.STOPS` and appear nowhere in the reference. One line naming them, or naming the count, removes the misreading. No runtime consequence. (E10 final review, 2026-08-04.) | 1 | C | ☐ |
| SK-143 | **E10 widened automatic archiving to cover half-finished sprints, and the Conventions line that said otherwise is gone.** Before E10 the run checklist's step 3 always refused on an id mismatch: the operator typed `init --archive` themselves, and the Conventions bullet read *"Archiving a half-finished sprint is an operator decision."* E10's step-3 fix — correct on its own terms, since `_undecided_review_refusal` fires only at `stage is REVIEW and G3 is None` and the prose was refusing where the CLI would have remediated — made every other state remediable. A sprint at `SCOPE`, `PLAN` or **`EXECUTE`** is now archived by the conductor with no question asked, because SK-115's refusal protects only the case where a *decision* is lost, not the case where *work in progress* is. Found on live turmarium, not in review: its `.supskill/` holds **B5 at EXECUTE with 6 DONE, one BLOCKED task and an open blocker**, and `/supskill run <new-id>` there would have closed it out silently. Nothing is destroyed — commits stay on the branch and `runs/<id>/*.jsonl` stays put — but the sprint's live state is retired without the operator ruling on it. Narrow the evidential branch: refuse when the on-disk sprint has any non-terminal task **or** any open blocker, not only when it rests at REVIEW with a null G3. Note this is a genuine regression introduced by E10, not a pre-existing gap, and it is consistent with the operator's own scope choice (gates and blockers interrupt; everything else is silent) — which is why it needs a mechanism rather than a reminder. (turmarium, 2026-08-04, immediately after the 0.7.0 install.) | 2 | M | ☐ |

**Sequencing.** SK-130 is the anchor and is planned first; SK-135 is its prose and
must follow it. SK-131 and SK-132 are independent of each other and of the rest.
SK-133 depends on SK-132 only for the `decide` half. SK-134 and SK-136 are
independent. Nothing here may ship before SK-130, because every other row's
behaviour is defined by which side of that table its stop falls on.

---

---

## Deferred / parked (not v1)

| ID | Item | Why parked |
|---|---|---|
| SK-090 | Backlog/PDD builder skill (backlog ← raw prose) | A separate product. `iterative-development` already does this half well; revisit after v1. |
| SK-091 | Multi-sprint auto-drain | Opt-in flag *after* the single-sprint loop earns trust. Plan staleness (**D6**) argues hard against it. |
| SK-092 | Git worktree isolation per sprint | Branch-per-sprint matches current practice. No evidence of pain yet. |
| SK-093 | Review `flow-next`'s "consent boundary" | The competitor agent spent its budget on `iterative-development`'s source. Open question §7.4. |

---

## Recommended first sprint

**S1 — The state spine (E1, 18 pts).**

Everything compounds on it: E2–E6 all mutate `state.json` and all depend on the preconditions in
SK-003 holding. It is also the **only epic that is pure Python** — meaning it is the one part of this
system that can be proven correct offline, fast, with real unit tests, before a single token is spent
on a subagent. And it structurally kills the scratch-dir collision (SK-004) that has been avoided by
ritual for seven sprints.

It is, in the vocabulary we stole, the **walking skeleton**: harness first, features after.

**Open question to settle at S1's Gate 1:** whether Gate 1 itself is always worth stopping for. The
blinkebot evidence cuts both ways — scope grew at refinement *every* sprint, which either proves the
gate always earns its keep or proves it is predictable enough to skip. Do not decide it here; decide
it with S1's own refinement pass as the first data point. (Report §7.2)

**Data point #2 (S2 DoR, 2026-07-12):** refinement against live source grew scope
+2 pts (10 → 12) and exposed a cross-epic gap — nothing populates `tasks[]`,
which would otherwise have surfaced as an E5 failure (now SK-033). Two sprints,
two data points, same direction. (Report §7.2)

**Data point #3 (S3 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (19 → 23), and the sharpest finding was again structural — a headless
conductor would have silently self-approved its own gate (`AskUserQuestion`
auto-resolves empty × `gate`'s by-design acceptance of empty responses), which
no backlog one-liner mentioned. The refusal now lives in the conductor
(SK-023). Three sprints, three data points, same direction. (Report §7.2)

**Data point #4 (S4 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (10 → 14), and — for the fourth consecutive sprint — the sharpest finding
was structural, not cosmetic: a headless PLAN stage could have executed the
entire sprint before its own approval gate (`writing-plans`' Execution Handoff
names a REQUIRED SUB-SKILL per branch), and an empty `tasks[]` made the spine's
strongest precondition a no-op. Neither is visible from a backlog one-liner.
Four sprints, four data points, same direction — §7.2 can be closed at E6 with
the answer *the gate earns its keep because the refinement does*. (Report §7.2)

**Data point #5 (S5 DoR, 2026-07-13):** refinement against live source grew scope
+4 pts (19 → 23), and — for the fifth consecutive sprint — the sharpest finding
was structural: **no verb in the CLI could mark a task done** (`cli.py:21-28`), so
`advance --to REVIEW` was unsatisfiable for any task that succeeded and no sprint
could ever reach REVIEW. Two of the pass's ten findings would have failed on the
first command of the first run: the derived scratch directory that nothing
creates, and Gate 2 still forbidding the very stage it opens. None of it is
visible from a backlog one-liner. Five sprints, five data points, same direction —
§7.2's answer at E6 stands: *the gate earns its keep because the refinement does.*
(Report §7.2)

**Data point #6 (S6 DoR, 2026-07-14):** refinement against live source grew scope
+4 pts (23 → 27) for the sixth consecutive sprint — the same magnitude as S3, S4
and S5, even though E6's own code did not exist yet and so carried no live
defects to find. The findings this time were about what was *absent* rather
than what was *wrong*: two verbs and a prompt template no story before this one
ever needed to build (SK-050), and a CLI value S1 itself flagged as deliberately
deferred (SK-051). Six sprints, six data points, same direction — §7.2's answer
holds a sixth time: *the gate earns its keep because the refinement does,
whether or not the code under review yet exists.* (Report §7.2)

**Data point #7 (S7 DoR, 2026-07-15):** for the first time in this backlog,
refinement against live source grew scope by **0 pts**. E7's stories are mostly
not-Python and mostly not-offline-provable, so the sharpest things the pass
found were not missing plumbing to build but claims the live world contradicts:
a repo already public, an "offline" eval whose named mechanism (`skill-creator`)
runs live, and a `v0.1.0` tag that resolves nothing at install. Correcting a
claim is not adding scope — the honest delta is 0 points and six corrections.
The gate still earned its keep: the corrections kept the plan from re-doing done
work, mislabelling a live spend as offline, or gating install on a tag. (Report
§7.2 — the refinement earns the gate whether it grows points or only fixes them.)
