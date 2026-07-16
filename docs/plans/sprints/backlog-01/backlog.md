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

**Total: 136 pts.** Expect this to grow — every blinkebot sprint grew its committed points at DoR
refinement, and there is no reason to believe this project is the exception. That growth is the
process working, not a planning failure.

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

## E7 — Packaging & distribution (9 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-060 | `marketplace.json` + first publish. **The plugin slug is immutable** — decide the name before this ships. | 3 | S | ☑ |
| SK-061 | `skill-creator` eval loop: should-trigger / should-not-trigger hit rate on the description. | 3 | S | ☑ |
| SK-062 | README + the build-in-public writeup for `bessavagner-page`. The lede is the finding, not the plugin: *"delegated agents cannot ask you anything — and in headless they silently receive an empty answer."* | 3 | C | ☑ |

## E8 — Validation (10 pts)

| ID | Story | Pts | Pri | Status |
|---|---|---|---|---|
| SK-070 | Fixture repo + toy two-sprint backlog; end-to-end run. Needs real LLM calls — manual and gated, not in the default suite. | 5 | M | ☐ |
| SK-071 | **Drive blinkebot S11 for real.** If it cannot run one sprint the operator would have run anyway, it does not ship. | 5 | M | ☐ |

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
