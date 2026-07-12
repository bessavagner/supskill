---
title: "supskill — design decisions"
date: 2026-07-12
status: approved (operator, 2026-07-12)
inputs:
  - contexts/01-claude-code-context-mechanics.md
  - contexts/02-skill-and-plugin-authoring.md
  - contexts/03-prior-art-and-landscape.md
  - contexts/04-composed-skill-contracts.md
  - contexts/05-empirical-workflow-blinkebot.md
  - contexts/06-competitor-source-review.md
purpose: >
  The record of what supskill is, why it is shaped this way, and what was
  deliberately rejected. A development backlog will be derived from this file.
---

# supskill — design decisions

## 1. The problem

Driving a backlog through `pm-execution:sprint-plan` → `superpowers:writing-plans` →
`superpowers:subagent-driven-development` requires the operator to manually clear context twice per
sprint and retype the invocation three times. Ten sprints of blinkebot were run this way. The
repetition is the visible cost; the real cost is that **the discipline lives entirely in the
operator's memory** — including the `.superpowers/sdd/` namespacing ritual, which has been
hand-copied verbatim into every sprint since S9 and which nothing enforces.

**supskill is a conductor**: it drives one sprint from a markdown backlog to a merged branch, drawing
a fresh-context boundary at every stage, holding three human gates, and keeping all authoritative
state on disk so it survives its own context death.

It is **not a methodology**. It composes skills the operator already trusts and adds no opinions
about how code gets written.

---

## 2. Decisions

### D1 — Build standalone. Do not wrap or fork `iterative-development`.

**Decided.** Verified against the competitor's *source*, not its README (`contexts/06`).

The steelman was serious: `prime-radiant-inc/iterative-development` already composes superpowers,
loops audited sprints, and drains a backlog. But reading its source shows it did not *miss* our
requirements — **it deliberately built their opposite**:

- Its design spec names Core Principle #9 **"Autonomous by default"**, and its escalation policy
  reads: *"Catastrophe-only… Ambiguity in the spec (make a reasonable judgment call)… Difficulty or
  slow progress (keep going)… The orchestrator does NOT prompt 'should I continue?'"* Our
  drain-then-halt boundary is the thing it explicitly engineered against.
- Its "Human Interrupt Protocol" is billed as out-of-band but means *the human types into the live
  chat session running the orchestrator*. It has **no file-based signal mechanism anywhere**, and
  therefore no answer at all for headless or subagent execution.
- It treats scope growth as **creep to be prevented** (a gate named for "scope-creep prevention").
  Our evidence says scope growth against live source is the *normal path*, every sprint.
- Its **input model runs backwards**: two of its six skills exist to *extract* a backlog from raw
  prose. We already have a backlog and need something to drive it. Those skills are dead weight.

Making it serve our design means rewriting the one skill that defines its identity, plus its
escalation policy and interrupt protocol wholesale. That is replacing the spine, not forking.

**Rejected alternatives:** wrap it (architecture actively resists); build without checking
(intellectually dishonest given we had the objection in hand).

### D2 — The loop lives in a skill; a script enforces the state transitions.

**Decided.** Hybrid, because neither pure option is safe.

There is **no deterministic "skill invokes skill" primitive** (`contexts/02`) — sequencing entrusted
to a skill is sequencing entrusted to model discretion, and a conductor that quietly skips the
plan-review gate on sprint six is worse than no conductor. But a pure shell driver abandons the
interactive session, which is the **only** place `AskUserQuestion` works — and the gates are the
product.

Resolution: the loop does not need to be deterministic *in the model*; it needs to be **verifiable
from disk**.

- The **skill** is the conductor UX. It runs in the operator's interactive session, dispatches each
  stage as a subagent (fresh context), and raises gates via real `AskUserQuestion`.
- The **script** (`supskill-state`, Python) is the only thing permitted to mutate `state.json`, and it
  validates preconditions on every transition. A model that tries to skip a gate fails the
  precondition and stops.

Note this is also a genuine differentiator: `iterative-development` puts *all* its control flow in
SKILL.md prose (its only scripts are format validators). Nothing there prevents the loop from
drifting.

### D3 — Promote "refine at pull time" to a first-class stage.

**Decided.** This is the heart of the design.

`sprint-plan` emits stories/points/risks. `writing-plans` expects a *spec* (architecture,
components) and assumes it came from `brainstorming`. Those are different altitudes, and the chain
does not actually compose (`contexts/04`).

But the bridge already exists — undocumented and manual. **Every sampled sprint doc carries a "DoR
findings (refined at pull time)" section** with file:line citations against current source, and every
one grew its committed points: S2e 10→16, S9 14→16, S10 18→23 (`contexts/05`). That refinement pass
*is* the sprint doc becoming spec-shaped.

Stage 2 does double duty:

1. Makes the sprint doc spec-shaped enough for `writing-plans` to consume (bridges the mismatch).
2. **Classifies every story by proof-seam** — which tells stage 4 what it can prove offline versus
   what must stop and wait for the operator. Without this, drain-then-halt has no principled basis
   for the split.

Scope growth becomes a *designed feature*, not a recurring surprise.

**Rejected:** inserting `superpowers:brainstorming` (Socratic, interactive, built for greenfield —
would fight the loop); bridging in the prompt only (drops the file:line-against-live-source
refinement, which is where the real gaps get caught).

### D4 — Escalation is out-of-band, and the executor drains before it halts.

**Decided.**

Inline asking is structurally impossible: `AskUserQuestion` is **stripped from subagents**, and in
headless/no-TTY it **auto-resolves in ~37ms with an empty answer** — closed "not planned", i.e.
intentional (`contexts/01`). A naive "ask the human when stuck" executor does not hang and does not
error; it silently receives nothing and proceeds. That is the exact silent-guessing failure the gate
exists to prevent, arriving through the mechanism meant to prevent it.

**Drain-then-halt:** every task not blocked and not downstream of a blocker runs to completion; each
blocked task parks with a structured record; then the sprint stops and escalates **all** accumulated
blockers as one high-information gate.

This is not invented — it is S9a's observed behaviour: 4 of 5 stories ran to green unattended, the
one needing a live LinkedIn capture hard-stopped and handed off (*"Controller does NOT drive LinkedIn
live… STOPS and hands off"*). Nothing was guessed.

It is also the honest answer to the rubber-stamp risk (see §4): **few, rich gates rather than many
thin ones.**

**Rejected:** halt-on-first-blocker (wastes proven unattended capacity, produces more and thinner
gates); best-effort guess-and-flag (S9a's working diagnosis was *wrong* — a guessing executor would
have "fixed" a parser that was never broken).

### D5 — Adopt SDD's status vocabulary. Do not invent a parallel protocol.

**Decided.** `subagent-driven-development` already reports `DONE / DONE_WITH_CONCERNS / BLOCKED /
NEEDS_CONTEXT` per task (`contexts/04`). supskill's job is to *listen properly* to a signal that
already exists. `BLOCKED` and `NEEDS_CONTEXT` park the task and write a blocker record;
`DONE_WITH_CONCERNS` proceeds but carries the concern into Gate 3.

A blocker record **must carry a recommendation and enumerate alternatives**, not merely report an
obstacle:

```
task: T3   kind: needs-live-capture
found:  entity parser returns 0 posts on all 23 profile reads
options: (a) operator drives a live capture now
         (b) defer to next sprint, proceed with the other 4 tasks
         (c) re-scope: the drift hypothesis may be wrong
recommend: (a) — the drift detector's heuristic may be firing misleadingly
```

That is S9a's real blocker. **Option (c) is the one that turned out to be correct** (the parser was
fine; `entity_posts_url` was dropping `/recent-activity/all/` on LinkedIn's opaque-id→slug redirect).
A record that said only "blocked" would have led the operator to (a) and stopped. Forcing the
executor to enumerate alternatives is what makes the gate generative rather than binary.

### D6 — v1 runs exactly one sprint per invocation.

**Decided.** `/supskill run S10` drives one sprint end to end, then proposes the next and stops.

**Plans go stale.** S10's plan written against today's tree is partly fiction once S9b lands and
moves the code beneath it — and the DoR evidence says scope grows against *live* source every single
sprint. A conductor that plans five sprints ahead writes four wrong plans. The loop can only honestly
run one sprint deep. This is the same insight that makes the gates valuable, not a limitation to work
around.

Multi-sprint auto-drain is an opt-in flag *after* the single-sprint loop earns trust.

### D7 — Sprints carry an entry point.

**Decided.** Not every unit of work enters at SCOPE. **S9b has a dev plan but no sprint doc** — it
skipped stage 1 entirely (`contexts/05`), because when a live finding overturns a diagnosis and forks
new work, the scope is already known and a sprint-doc stage would be ceremony.

`state.json` records `sprint.entry` ∈ `SCOPE | PLAN | EXECUTE`. Same machine, different entry point.
Costs nothing — the precondition checks must exist regardless.

### D8 — Scratch paths are derived, never typed.

**Decided.** `sprint.scratch` is computed from the sprint id (`.superpowers/sdd/<sprint-id>/`) and
passed to SDD via the `OUTFILE` override that `task-brief` and `review-package` already accept.

The collision is real and confirmed: `task-N-{brief,report,review}.md` is namespaced by task number
only, task numbering restarts each sprint, so two sprints' "Task 3" silently overwrite each other.
The current fix is **100% memory-carried** — every controller since S9 copies an identical boilerplate
paragraph citing the memory tag, by hand, every time (`contexts/05`). That is a ritual, not a
convention. This bug class must be **structurally impossible**, not conventionally avoided.

### D9 — Steal Parallel Adversarial Review for the review gate.

**Decided.** From `iterative-development` (`contexts/06`): dispatch two reviewer subagents on
identical input, wrapped in a fixed competitive-scoring frame (*"false positives are worse than
misses"*), and aggregate by fixed rule — same finding from both → high confidence; one only → still
actionable; **severity disagreement → always take the worse one, no negotiation.**

Justified independently by the research: agents are documented poor self-certifiers, reporting
confidently on mediocre work (`contexts/03`). S9 shipped green with 410 tests and its whole-branch
review still found five mechanisms with **zero production callers**. Reviewer sycophancy is a real
failure mode and PAR is a cheap countermeasure.

Also stolen: the **proof-seam / impact taxonomy** (`seam: unit|integration|app-level|e2e`,
`impact: none|local|cross-surface|journey`) as the vocabulary for D3's offline-vs-operator
classification.

---

## 3. The design

### Stages

```
  backlog.md
      │
  [1] SCOPE      sprint-plan → sprint doc (stories, points, risks)
      │
  [2] REFINE     read live source, cite file:line, surface gaps, grow the scope,
      │          classify each story by proof-seam (offline | operator)
      │          → sprint doc becomes spec-shaped
      │
      ├──────────► GATE 1: operator reads the refined sprint doc
      │
  [3] PLAN       writing-plans → dev plan (tasks)
      │
      ├──────────► GATE 2: operator reads the plan
      │
  [4] EXECUTE    subagent-driven-development, drain-then-halt
      │
  [5] REVIEW     PAR: two adversarial reviewers, worse severity wins
      │
      └──────────► GATE 3: batched blockers + review findings
                   → one of four replan shapes
                   → propose next sprint, stop
```

Each stage is a subagent with a fresh context, producing exactly one artifact on disk. The conductor
holds no state in its head; `/clear` and re-invoke resumes mid-sprint from `state.json`.

### The four replan shapes (Gate 3 output)

| Shape | Real instance | Effect on the backlog |
|---|---|---|
| Review generates new items | S9 → S9a | Appends new `pending` rows |
| Execution stops at a live boundary | S9a | Parks a task; sprint stays open |
| Live evidence overturns the diagnosis | S9a → S9b | Forks a new sprint + branch rename; **operator rules on process weight before any code** |
| North-star reset | backlog-01 → 02 | **Supersedes** the whole backlog |

The first three *amend*. The fourth *replaces*, is operator-authored, and the conductor must **refuse
to perform it autonomously**.

### State

`.supskill/state.json` is the single source of truth. Two append-only logs sit beside it:

```
.supskill/
  state.json              # authoritative; the only file the conductor reads to resume
  gates.jsonl             # every gate decision + the operator's verbatim response (audit trail)
  runs/<sprint-id>/
    blockers.jsonl        # every blocker record raised during execution
```

Task statuses: `PENDING` → `DONE` | `DONE_WITH_CONCERNS` | `BLOCKED` (this task itself is stuck) |
`PARKED` (this task is fine but sits downstream of a blocked one, so it may not run).

```json
{
  "schema": 1,
  "backlog": "docs/plans/sprints/backlog-02/backlog.md",
  "sprint": {
    "id": "S10", "slug": "alerting-spine", "entry": "SCOPE",
    "branch": "feat/e10-alerting-spine",
    "scratch": ".superpowers/sdd/s10/"
  },
  "stage": "REFINE",
  "artifacts": { "sprint_doc": "…", "dev_plan": null },
  "gates": { "G1_sprint_doc": null, "G2_plan": null, "G3_review": null },
  "tasks": [ { "id": "T3", "seam": "e2e", "provable": "operator", "status": "BLOCKED" } ],
  "blockers": [ { "task": "T3", "kind": "…", "found": "…", "options": ["…"], "recommend": "…" } ]
}
```

`supskill-state` (Python) exposes `init | advance | gate | block | show`. Preconditions:

- `advance --to PLAN` requires the sprint doc to exist **and** `G1 == approved`
- `advance --to EXECUTE` requires `G2 == approved`
- `advance --to REVIEW` requires every task terminal (`DONE | BLOCKED | PARKED`)

### Known limitation (stated, not dressed up)

**The script cannot prove a human answered a gate.** It sees `gate --id G1 --decision approved`; it
cannot distinguish the operator from a model that decided to keep things moving. No harness primitive
gives a trustworthy human-presence signal.

What we get instead: gate-skipping becomes **loud and auditable rather than silent**. Every gate call
appends the operator's verbatim response to an append-only `gates.jsonl`; a fabricated approval leaves
an empty or invented quote in a log the operator can read.

This is real protection against the actual failure mode — a model drifting past a checkpoint because
the instructions got long — and no protection against a determined adversary. Accepted as the right
trade.

---

## 4. The strongest objection, and the answer

Anthropic's own platform research measured **93% rubber-stamp approval on permission prompts** and
moved the platform toward environmental containment *over* per-action gates (`contexts/03`). Three
gates per sprint across a long backlog is a lot of decision points. The objection: supskill may build
an elaborate machine for manufacturing the *illusion* of oversight.

**The answer is empirical, from the operator's own history.** The 93% figure concerns *per-action*
approvals — high-frequency, low-information, mid-flow. These gates are none of those. Every gate
examined across ten sprints **changed the outcome**:

- Refinement grew committed scope on **every single sprint** (10→16, 14→16, 18→23).
- The S9 whole-branch review found five mechanisms that passed tests but had **zero production
  callers**, including a live blocker where the entity parser returned 0 posts on all 23 profile
  reads. S9 was already marked *done*. Those findings became S9a.
- S9a's live gate **disproved its own working diagnosis** and forked S9b.

A gateless pipeline ships S9 as "done" and finds none of it. The design responds to the objection
directly by **batching blockers into few, rich gates** (D4) rather than emitting many thin ones, and
by keeping gates at genuine decision points — the discipline LangGraph advocates ("gate sparingly").

---

## 5. Scope

**In v1:** the five stages, three gates, the four replan shapes, `state.json` + `supskill-state`
enforcement, derived scratch paths, PAR review, drain-then-halt, entry points.

**Explicitly not in v1** (each a real temptation):

- No backlog-builder / PDD-builder skill (future).
- No multi-sprint auto-drain (opt-in flag, only after the single-sprint loop earns trust).
- No git worktrees (branch-per-sprint matches current practice).
- No support for any chain but this one.

**Validation:** v1 is built by hand, then earns its keep by driving **blinkebot S11** for real. If it
cannot run one sprint the operator would have run anyway, it does not ship.

---

## 6. Packaging

A Claude Code plugin. `.claude-plugin/plugin.json`; components (`skills/`, `agents/`, `scripts/`) at
plugin **root**, not inside `.claude-plugin/`. Distributed from the operator's own GitHub marketplace.
The plugin slug is **immutable once published** — name chosen once.

The skill's `description` must state **only triggering conditions** and must not summarize its own
workflow: `superpowers:writing-skills` records a regression where a workflow-summarizing description
caused an agent to skip half the required process (`contexts/02`).

Testing:

- `supskill-state` is plain Python → **real unit tests** on the preconditions (*can you advance to
  EXECUTE with `G2 == null`? No.* *Does S9a's scratch path differ from S9's?*). Fast, offline, and
  they cover exactly the bug classes this exists to prevent.
- Prompts → eval-driven via the official `skill-creator` (should-trigger / should-not-trigger).
- End-to-end → a fixture repo with a toy two-sprint backlog. Requires real runs; manual and gated.

---

## 7. Open questions (for the backlog, not blockers)

1. **Name.** "supskill" is the working title; the published slug is immutable, so decide before first
   publish.
2. **Gate 1 necessity.** Is the refined sprint doc always worth a gate, or only when refinement grew
   scope past a threshold? Evidence says scope grew every time — but that may argue the gate is
   *always* warranted, or that it is *predictable enough to skip*. Unresolved.
3. **PAR cost.** Two reviewers per sprint review doubles that stage's token cost. Worth measuring
   against the S9 case (which a single reviewer *did* catch).
4. **`flow-next`** was never reviewed (the competitor agent spent its budget on
   `iterative-development`'s source instead). Its "consent boundary" concept may hold ideas worth
   stealing.
5. **Build-in-public artifact.** The finding — *subagents can't ask questions, and in headless they
   silently receive an empty answer* — is the strongest post in here, and it generalizes well beyond
   this plugin.
