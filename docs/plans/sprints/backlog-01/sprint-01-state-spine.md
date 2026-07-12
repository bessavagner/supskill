# Sprint 01 — The state spine (walking skeleton)

**Epic:** E1 · **Points:** 21 committed (was 18 — see [DoR findings](#dor-findings-refined-at-pull-time)) · **Milestone:** the gates cannot be skipped, and that claim is proven by a fast, offline test suite before a single token is spent on a subagent.
**Depends on:** nothing — this is the first sprint; the repo itself does not exist yet (SK-007 bootstraps it) · **Unblocks:** E2 (the conductor resumes from `state.json` alone), E3–E6 (every stage mutates state through this CLI and nothing else), and it discharges the backlog's DoR note on SK-003/SK-006.
**Reference:** [backlog-01](backlog.md) — north star, invariants, findings F-1…F-5 · [design decisions](../../../.ai/reports/2026-07-12-supskill-design-decisions.md) — **D2** (schema + preconditions), **D4** (drain-then-halt), **D5** (SDD vocabulary + blocker record), **D7** (entry points), **D8** (derived scratch) · [contexts/04](../../../.ai/reports/contexts/04-composed-skill-contracts.md) — the verbatim SDD contract this spine must listen to.

## Sprint goal (one line)

> A `supskill-state` CLI whose precondition checks make gate-skipping fail loudly — `advance --to EXECUTE` with `G2 == null` **refuses** — with every decision and blocker on disk in append-only logs, so a conductor with amnesia can resume mid-sprint from `state.json` alone.

## Why this sprint

Everything compounds on it. E2–E6 all mutate `state.json`, and all of them depend on SK-003's preconditions holding — a conductor built before the spine is a conductor whose discipline lives in prose, which is exactly the failure mode D2 exists to close (`iterative-development` puts *all* its control flow in SKILL.md prose, and nothing there prevents the loop from drifting).

It is also the **only pure-Python epic** — the one part of this system provable correct offline, fast, with real unit tests. The design's own testing section (§6) names the two tests that matter verbatim: *can you advance to EXECUTE with `G2 == null`? No.* and *does S9a's scratch path differ from S9's?* This sprint ends when those tests exist and pass.

And it structurally kills the scratch-dir ritual: `task-N-{brief,report}.md` is namespaced by task number only, task numbering restarts every sprint, and the current fix is a boilerplate paragraph hand-copied into every controller prompt since blinkebot S9 (D8). SK-004 makes the collision **impossible**, not avoided.

Two constraints shape every story here:

1. **The script is the only mutator of `state.json`** (invariant 3). Nothing in E2–E6 may write it directly; the reviewer checks this now and on every future sprint. The spine is the enforcement mechanism, so the spine itself must be boring, small, and dependency-free.
2. **The conductor is disposable** (invariant 5). `state.json` is the resume mechanism after `/clear` or a crash — so writes must be atomic and the audit logs append-only. A truncated `state.json` is not a bug in the conductor; it is the death of the product's core promise.

## Capacity & sequencing

Working capacity ~**34 pts**; ~18% buffer → ~**28 pts committable** (capacity model inherited from the blinkebot backlog README — same operator, same fleet). Committed: **21 pts** → single wave, ~7 pts of headroom.

The headroom is deliberate: this is the first sprint of a greenfield repo, and the plan-time pass (`writing-plans`) has no live source to refine against yet — expect task-level discoveries to eat some of it. **Do not fill the 7 pts.** Nothing here is droppable — all six original stories are load-bearing and SK-007 is the floor they stand on; if the sprint tightens, trim `show`'s output polish (SK-002), never a precondition.

- **Critical path:** SK-007 (scaffold) → SK-001 (schema — every other story imports its types) → SK-003 (preconditions — the single most important story in the backlog).
- **After SK-001 lands**, SK-002 / SK-004 / SK-005 / SK-006 are independent and may run in parallel worktrees.
- **SK-003 goes last.** It consumes SK-001's terminal-status constant, SK-005's gate state, and SK-002's entry semantics; sequencing it after them means its tests exercise the real seams, not stubs.

## Stories

### SK-007 — Repo & package scaffold · 2 · M · **(new at pull time)**

- **As** the test suite E1 exists to deliver, **I want** a Python package with a test harness, **so that** "pure-Python, unit-testable, offline" has somewhere to run — today the repo contains only docs.

- **Context (why this exists — see DoR finding 3).** The backlog calls E1 "the only pure-Python unit-testable part," but there is no `pyproject.toml`, no `tests/`, no lint config — no repo at all in the git sense. Packaging (design §6) puts components (`skills/`, `agents/`, `scripts/`) at plugin **root**; the scaffold must not fight that layout when SK-010 (E2) adds them.

- **Accept:**
  - `git init` + `pyproject.toml`; `pytest` and `ruff check` run green, offline, in seconds.
  - The state tool is an importable **package** (e.g. `scripts/supskill_state/`) with a thin CLI entry shim — the suite imports functions directly; nothing shells out to test logic. A CLI-only script that can only be tested by subprocess is the wrong shape.
  - **Zero runtime dependencies beyond the stdlib** (argparse/json/dataclasses). The plugin runs on whatever Python the operator's machine has; a `pip install pydantic` step before the conductor can hold a gate is a distribution bug. Decided at brainstorming, recorded in the plan.
  - Layout leaves room for `.claude-plugin/plugin.json` and root-level `skills/`/`agents/` (SK-010) without moving anything.

### SK-001 — `state.json` schema v1 + typed read/write · 3 · M

- **As** the disposable conductor, **I want** a typed, versioned, atomically-written `state.json`, **so that** resume-from-disk is a load, not an archaeology dig.

- **Context.** D2's schema block is the contract — round-trip **every** field in it. Two traps found at pull time (DoR findings 1 and 4): the task-status enum must **not** contain SDD's `NEEDS_CONTEXT` (it is a controller-loop signal, not a persistable state), and the write path must be atomic because this file is the resume mechanism (invariant 5).

- **Accept:**
  - Typed model covering every field of D2's example (`schema`, `backlog`, `sprint{id, slug, entry, branch, scratch}`, `stage`, `artifacts`, `gates`, `tasks[{id, seam, provable, status}]`, `blockers[]`); `load(dump(x)) == x` asserted field-by-field against a fixture that mirrors D2's example verbatim.
  - `schema: 1` checked on load. An unknown schema version **refuses loudly** — no silent migration, no best-effort parse. (Migration machinery is deferred until a schema 2 exists to migrate to.)
  - Task status enum is exactly `PENDING | DONE | DONE_WITH_CONCERNS | BLOCKED | PARKED`. `NEEDS_CONTEXT` is rejected as a status value; the mapping (→ resolve in-loop, else `BLOCKED` + blocker record, per D5) is documented where E5 will find it. The **terminal set** `{DONE, DONE_WITH_CONCERNS, BLOCKED, PARKED}` is exported as a constant — SK-003 consumes it; nothing redefines it.
  - Stage enum covers `SCOPE | REFINE | PLAN | EXECUTE | REVIEW`; `sprint.entry` ∈ `SCOPE | PLAN | EXECUTE` (D7). Whether sprint-completion is a sixth stage or a G3 decision is decided at brainstorming and recorded — not left implicit.
  - **Writes are atomic**: temp file + rename in the same directory. A process killed mid-write leaves the previous valid state, never a truncated file. Asserted (write a partial temp, prove load ignores it).
  - **One datetime convention, stated now**: timezone-aware UTC, ISO-8601, everywhere — schema doc says so and a test enforces it on every timestamp field. blinkebot paid for its naive/aware split with a permanent `_aware()` shim; supskill starts with zero conventions to reconcile (DoR finding 5).

### SK-002 — `supskill-state init | show` · 3 · M · **(2 → 3 at pull time)**

- **As** the operator, **I want** to create a sprint run and see where it stands, **so that** "what stage am I in, what's blocked, what did the gates say" never requires reading raw JSON.

- **Context (why it grew — DoR finding 2).** D7 says sprints carry an entry point (`SCOPE | PLAN | EXECUTE` — S9b skipped straight to EXECUTE, and a sprint-doc stage there would have been ceremony), but E1's backlog one-liners never say *who honors it*. SK-013 (E2) reads `sprint.entry`; the machine that makes entry coherent — init at an arbitrary stage without corrupting SK-003's preconditions — lives **here**.

- **Accept:**
  - `init` creates `.supskill/state.json`, an empty `gates.jsonl`, and `runs/<sprint-id>/`; derives `sprint.scratch` via SK-004. It **refuses** when a `state.json` already exists; overriding requires an explicit flag and archives the old state under `runs/<old-sprint-id>/` — prior state is never destroyed.
  - `init --entry SCOPE|PLAN|EXECUTE` (default `SCOPE`) sets `stage` to the entry point; anything else is rejected. A sprint entering at `EXECUTE` starts there with all gates `null` — legal, because preconditions attach to **transitions**, not stages (see SK-003). Both entry shapes asserted.
  - `show` prints stage, each gate's state, task counts by status, and open blockers — readable in one glance. With no `state.json`: a clear message and a nonzero exit, not a stack trace.

### SK-003 — `advance --to <STAGE>` with precondition validation · 5 · M

- **As** the product's entire reason to exist, **I want** every stage transition validated against preconditions the model cannot talk its way past, **so that** a conductor that quietly skips the plan-review gate on sprint six is structurally impossible. **This is the enforcement mechanism — the single most important story in the backlog.**

- **Context.** D2's preconditions, verbatim: `PLAN` requires the sprint doc **and** `G1 == approved`; `EXECUTE` requires `G2 == approved`; `REVIEW` requires every task terminal. Pull-time refinement adds two resolutions: preconditions attach to *transitions taken*, not stages (which is how D7's entry points coexist with D2's checks — a sprint that *starts* at EXECUTE never crosses the G2 check; one that starts at SCOPE cannot reach EXECUTE without both gates), and `advance` is strictly one-step-forward (the replan shapes that move backwards are E6's explicit verbs, never a loosened `advance`).

- **Accept:**
  - `advance --to PLAN` refused unless `artifacts.sprint_doc` exists **and** `G1 == approved`. `--to EXECUTE` refused unless `G2 == approved` **and** `artifacts.dev_plan` exists. `--to REVIEW` refused while any task's status is outside SK-001's terminal set (`PENDING` and any unrecognized value are non-terminal). A gate that is `null`, `rejected`, or anything but `approved` refuses.
  - Refusal is a **nonzero exit + a reason naming the failed precondition** — and `state.json` is untouched on refusal (asserted byte-identical before/after).
  - Only one-step-forward transitions (`SCOPE→REFINE→PLAN→EXECUTE→REVIEW`) are expressible. Skipping a stage via `advance` is impossible regardless of gate state.
  - Entry-aware, asserted both ways: `init --entry EXECUTE` then (all tasks terminal) `advance --to REVIEW` **succeeds** with G1/G2 null; `init --entry SCOPE` can never reach EXECUTE without G1 and G2 approved, whatever sequence of calls is attempted.
  - The design's own named test exists verbatim: *can you advance to EXECUTE with `G2 == null`? **No.*** (design §6).

### SK-004 — Derive `sprint.scratch` from the sprint id · 2 · M

- **As** every sprint that will ever share this repo with another, **I want** my SDD scratch path computed from my id, **so that** two sprints' "Task 3" briefs can never silently overwrite each other again. Kills the hand-copied ritual. (**D8**)

- **Context.** The collision is confirmed and by design: SDD's `task-brief`/`review-package` default everything into one repo-wide `.superpowers/sdd/`, namespaced by task number only — and both scripts accept an `OUTFILE` override as their third argument, which is the seam supskill leans on (contexts/04, mismatch 3). Implementer *reports* are not script-generated at all (the controller composes those paths by hand), so the derived directory is the base for **all** per-sprint scratch, not just the two script outputs — E5 consumes it; this story only derives and stores it.

- **Accept:**
  - `sprint.scratch = .superpowers/sdd/<normalized-id>/`, derived at `init`, stored in `state.json`. **No flag accepts a user-typed scratch path — the option must not exist** (derived, never typed).
  - Normalization is deterministic and loud: lowercase; only `[a-z0-9-]` accepted; anything else **rejected**, never silently mangled (two ids must never normalize into the same path). `S9` and `s9` are the same sprint; `s9` and `s9a` are not.
  - The design's own named test exists verbatim: *does S9a's scratch path differ from S9's?* — plus a property-style test that distinct normalized ids always yield distinct paths.

### SK-005 — `gate --id <G> --decision <d> --response <verbatim>` · 3 · M

- **As** the operator reading the audit trail after something went sideways, **I want** every gate decision appended to `gates.jsonl` with my verbatim words, **so that** a fabricated approval leaves a readable trace. The audit trail is the whole point (F-4).

- **Context.** F-4 is the honest ceiling: the script **cannot prove a human answered** — what it buys is that gate-skipping becomes *loud and auditable*, not impossible. That cuts one way that matters here: an empty `--response` must be **accepted and recorded**, not rejected — the design explicitly wants a fabricated approval to leave an empty or invented quote in a log the operator can read. Rejecting it would just teach a drifting model to invent a plausible quote. Also found at pull time: the write **order** is load-bearing (DoR finding 4).

- **Accept:**
  - `gate --id G1|G2|G3 --decision <approved|rejected> --response <verbatim>` appends `{gate, decision, response, at}` (aware UTC) to `gates.jsonl` and updates `state.json.gates`. CLI ids `G1/G2/G3` map onto the schema's gate keys one-to-one; the mapping is recorded in the schema doc, not folklore. (The decision vocabulary is deliberately minimal — G3's four replan shapes are E6's to add.)
  - **Append-only, structurally**: the command opens for append and never truncates or rewrites. A second decision on the same gate appends a new record — history preserved — and last-wins in `state.json`. Asserted.
  - **Write order: `gates.jsonl` first, then `state.json`.** A crash between the two leaves the audit trail *ahead of* state, never behind — a decision may need re-applying, but it can never have silently not happened. Asserted by failing the second write in a test.
  - An empty `--response` is accepted, recorded, and visible in `show` — loud, per F-4.

### SK-006 — `block` → structured blocker records · 3 · M

- **As** the operator woken by an escalation, **I want** every blocker to arrive with enumerated options and a recommendation, **so that** the gate is a decision, not an acknowledgment — a bare "blocked" would have misled me on S9a. (**D5**)

- **Context.** D5's fixture is the spec: S9a's real blocker carried three options, the *recommended* one (a) was wrong, and option (c) — a re-scope, "the drift hypothesis may be wrong" — was right. The value was in the **enumeration**: forcing alternatives into the record is what made the wrong recommendation survivable. Refined against SDD's real contract (contexts/04 §3): the implementer reports exactly four statuses; `BLOCKED` and unresolvable `NEEDS_CONTEXT` are the two that become blocker records (E5 does that mapping — this story provides the record it maps *into*).

- **Accept:**
  - `block --task <id> ...` appends the record to `runs/<sprint-id>/blockers.jsonl` (append-only), mirrors it into `state.json.blockers`, and sets the task's status to `BLOCKED` — one command, three effects, asserted together.
  - Schema **requires** `task`, `kind`, `found`, `options[]`, and `recommend`. `options` must contain **at least two** entries — an escalation offering one option is a fait accompli, not a decision — and `recommend` must reference one of them. A record missing any of these is **rejected**: nonzero exit, nothing written anywhere. Asserted per missing field.
  - D5's verbatim S9a blocker round-trips as a fixture.
  - Scope boundary, stated: this command records **one** blocker. Computing the downstream cone of tasks to `PARK` is E5's drain logic, not `block`'s.

## DoR findings (refined at pull time)

E1 is greenfield — there is no live source to cite `file:line` against — so this refinement pass ran against the next-best authoritative sources: D2's schema and preconditions, D7/D8, and the **verbatim SDD contract** in contexts/04 (exactly what the backlog's DoR note demanded for SK-003/SK-006). Sprint goes **18 → 21 pts** (SK-007 added at 2; SK-002 2 → 3), well under the 28-pt guardrail.

1. **`NEEDS_CONTEXT` is not a state, and the status enum must say so** (shapes SK-001, discharges half the DoR note). SDD's implementer contract has exactly four values — `DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED` — but `NEEDS_CONTEXT`'s defined handling is *"controller supplies missing info, re-dispatches same subagent"* (contexts/04 §3): it is a loop signal, not a resting state. D2's task enum (`PENDING → DONE | DONE_WITH_CONCERNS | BLOCKED | PARKED`) is therefore correct to omit it — but only if the mapping (resolve in-loop, else `BLOCKED` + blocker record, per D5) is written down now, where E5 will find it, and the terminal set is exported as a constant SK-003 consumes rather than redefines.

2. **Preconditions attach to transitions, not stages** (shapes SK-002/SK-003; grew SK-002 2 → 3). D7's entry points and D2's preconditions look like they collide — how does a sprint `init`'d at `EXECUTE` satisfy "EXECUTE requires `G2 == approved`"? Resolution: it never *advances to* EXECUTE, so it never crosses that check; a SCOPE-entry sprint must cross both. D7's claim that entry "costs nothing" is almost true — the cost it does have (entry-aware `init`, both shapes asserted) lands in SK-002.

3. **There is no repo** (adds SK-007). The backlog calls E1 "the only pure-Python unit-testable epic," but the workspace contains only docs — no `pyproject.toml`, no test harness, no lint config. And the shape matters: an executable-script-only layout can only be tested by subprocess, so the state tool must be an importable package with a thin CLI shim, stdlib-only (the plugin runs on whatever Python the operator has).

4. **The audit trail's write order is load-bearing** (shapes SK-005, and SK-001's atomicity). Two files record each gate decision (`gates.jsonl`, `state.json`); a crash between the writes must leave the trail *ahead of* state, never behind — F-4's entire value is that the log never understates what happened. Same reasoning makes `state.json` writes atomic (temp + rename): it is the resume file (invariant 5), and a truncated resume file kills the disposable-conductor promise.

5. **One datetime convention, from birth** (shapes SK-001). blinkebot mixed naive `utcnow` and aware `now(timezone.utc)` and pays for it with a permanent `_aware()` shim and a recurring risk-table row. supskill has zero timestamps today; schema v1 states aware-UTC ISO-8601 everywhere and a test enforces it. Cheapest bug this project will ever prevent.

**Deliberately NOT in scope**, though tempting: the conductor skill and resume UX (E2 — the spine is proven by tests, not by driving it), any subagent dispatch, the REFINE agent, backwards/replan transitions (E6's explicit verbs), multi-sprint state, and schema-migration machinery (nothing exists to migrate).

**Gate 1 data point** (open question §7.2, to be settled at this sprint's own Gate 1): this refinement pass grew scope 18 → 21 and surfaced two contract resolutions (findings 1–2) the one-liners could not encode — consistent with the blinkebot pattern that refinement always earns its keep. One data point; decide at the gate, not here.

## Skills for executors

Standing skills apply to every story (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits — per the blinkebot standing rules, which this repo adopts). Domain additions:

- **Whole sprint** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`. Failing test first. **The suite is pure offline** — no LLM, no subagent, no network, no git-remote anywhere in it; if a test wants a model, the design is wrong.
- **SK-007** — plain scaffold; `context7` for current `pyproject`/pytest/ruff idioms rather than memory.
- **SK-001** — `superpowers:brainstorming` **first**: the schema shape is the seam every epic reads, and two decisions (stdlib-vs-dependency, terminal-stage-or-G3-decision) must be made once, on purpose. Then `python-pro` + `tdd`; the round-trip fixture and the atomic-write kill test are the gates.
- **SK-003** — `oh-my-claudecode:architect` consult on the transition machine (entry points × preconditions × one-step-forward — E2–E6 all live downstream of this being right); `python-pro` + `tdd`. The named `G2 == null` refusal test is the gate.
- **SK-004 / SK-005 / SK-006** — `python-pro` + `tdd`; may run in parallel worktrees (`superpowers:using-git-worktrees`). SK-005's write-order assertion and SK-006's reject-on-missing-field assertions are the gates.
- **Review pass** — `oh-my-claudecode:code-reviewer` → `oh-my-claudecode:verifier`. No security-reviewer needed (no secrets, no egress) — but the reviewer explicitly checks invariant 3: **no code path outside `supskill-state` writes `state.json`**, a check that repeats on every future sprint.

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **Status vocabulary drifts from SDD's real contract** and E5 discovers the mismatch three sprints from now | executor (001) | E5's mapping needs a status the enum lacks, or vice versa | The enum and the `NEEDS_CONTEXT` mapping are copied from contexts/04's verbatim quotes **now**; E5 adopts the exported constant, never redefines it. (**D5**: listen, don't invent.) |
| **Preconditions honored in spirit, bypassable in practice** — the model edits `state.json` by hand | — | a stage advanced with no corresponding CLI call in history | Known, accepted ceiling (F-4): the protection is loud auditability, not tamper-proofing. Do **not** gold-plate this — the design already ruled. |
| **Entry points punch a hole in the gate checks** (an `--entry EXECUTE` sprint used to dodge G2 on work that needed it) | executor (002/003) | gates all null on a sprint that plainly had a plan stage | Transition-attached preconditions + both entry shapes asserted (SK-003). Choosing the entry honestly is the operator's call at `init` — D7 trusts it by design. |
| **A crash mid-write corrupts the resume file** | executor (001) | truncated/unparseable `state.json` after a kill | Atomic temp+rename, asserted with a partial-write test. The trail (`gates.jsonl`) is append-only and written **first** (SK-005). |
| **Schema over-engineering** — pydantic, migrations, generality nobody asked for | executor (001) | a dependency appears in `pyproject`, or migration code with one schema version | stdlib-only (SK-007); `schema: 1` refuses unknown versions and that is the whole migration story until schema 2 exists. |
| **Two sprint ids silently normalize to one scratch path** | executor (004) | `S9`-vs-`s9`-style aliasing, or a mangled id colliding | Reject non-canonical characters loudly; property test that distinct normalized ids ⇒ distinct paths. |
| Plan-time discoveries outgrow the headroom | operator | `writing-plans` surfaces >7 pts of new work | Greenfield cuts both ways — no legacy to fight, but no source to have refined against either. Trim `show` polish first; **never** trim a precondition or an append-only property. |

## Exit criteria

- [ ] **SK-007:** `pytest` + `ruff check` green, offline, in seconds; state tool importable as a package with a thin CLI shim; zero runtime deps beyond stdlib; layout compatible with the plugin-root component convention.
- [ ] **SK-001:** D2's example round-trips field-by-field; unknown `schema` refused; status enum exact with the terminal set exported (and `NEEDS_CONTEXT` rejected); atomic write proven by a kill/partial-write test; every timestamp aware-UTC ISO-8601, enforced by test.
- [ ] **SK-002:** `init` refuses to clobber (archive requires an explicit flag, old state preserved); `--entry` honored for all three values with `stage` set accordingly; `show` readable with a sane no-state failure mode.
- [ ] **SK-003:** all three preconditions refuse with a named reason and byte-identical `state.json`; one-step-forward only; entry-aware both ways; **the design's own test passes verbatim: `advance --to EXECUTE` with `G2 == null` → refused.**
- [ ] **SK-004:** scratch derived at `init`, no user-typed override exists; loud normalization; **S9a's path ≠ S9's**, plus the distinct-ids ⇒ distinct-paths property.
- [ ] **SK-005:** decisions append to `gates.jsonl` (never truncate; history preserved, last-wins in state); trail-before-state write order asserted; empty verbatim response accepted and visible.
- [ ] **SK-006:** record rejected per missing field (`options[]` ≥ 2, `recommend` references an option); accepted record lands in `blockers.jsonl` + `state.json` + flips the task to `BLOCKED` atomically as one command; the S9a fixture round-trips.
- [ ] **Reviewer confirms invariant 3:** no code path outside `supskill-state` writes `state.json`.
- [ ] Full suite offline and fast (seconds, not minutes); `ruff` green; every story TDD'd with the failing-test-first evidence in the SDD scratch dir.
- [ ] **The sprint demo (the north star in miniature):** `init s1` → `gate --id G1 --decision approved --response "<the operator's actual words>"` → `advance --to PLAN` succeeds → `advance --to EXECUTE` **refuses, loudly, naming G2** → `gates.jsonl` shows the whole story in order. Then: kill the process mid-write and resume from a valid `state.json`.

> **Honest scope note:** S1 proves the spine in tests, not in anger. No conductor exists yet to *use* these preconditions (E2), no stage produces the artifacts they check for (E3–E5), and F-4's ceiling stands — a determined model can still call `gate` itself; what it cannot do is leave no trace. The first end-to-end proof that the spine holds under a real sprint is E8's job, and the first *operational* proof is E2's `/clear`-and-resume test.

## Backlog deltas — proposed (not yet applied)

To be applied to [backlog.md](backlog.md) once the operator accepts this doc:

1. **SK-007 added to E1 (2 pts):** repo & package scaffold — pyproject + pytest + ruff, importable package + thin CLI shim, stdlib-only. E1's "pure-Python, unit-testable" claim had nowhere to run.
2. **SK-002 re-scoped and re-pointed 2 → 3:** `init` gains `--entry SCOPE|PLAN|EXECUTE` (D7) with the transition-attached precondition semantics recorded; refuses to clobber existing state without an explicit archive flag.
3. **SK-001's note records the two conventions:** task-status enum excludes `NEEDS_CONTEXT` (loop signal, not a state — mapping per D5 documented for E5), and all timestamps are aware-UTC ISO-8601 from schema v1.
4. **SK-005's note records the write order:** `gates.jsonl` before `state.json`, and that an empty verbatim response is accepted-and-recorded by design (F-4), not rejected.
5. **E1 total 18 → 21; Summary table and 115-pt total updated accordingly** — growth at DoR refinement, the process working as designed.
6. **First data point on open question §7.2 (Gate 1 necessity) recorded:** greenfield refinement against design docs alone grew scope +3 pts and resolved two contract ambiguities. To be weighed at this sprint's Gate 1.
