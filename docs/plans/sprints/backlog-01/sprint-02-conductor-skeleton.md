# Sprint 02 — Conductor skill + plugin skeleton

**Epic:** E2 · **Points:** 12 committed (was 10 — see [DoR findings](#dor-findings-refined-at-pull-time)) · **Milestone:** invoke, read state, resume — a conductor with amnesia (`/clear`, crash, fresh terminal) lands on the right stage from `state.json` alone, and the repo is a valid Claude Code plugin.
**Depends on:** S1 — the state spine landed in full (`init | show | artifact | gate | block | advance`, commits `6f3cb4f…b318a9f`), including the `artifact` verb added as a plan-time discovery · **Unblocks:** E3–E6 (every stage needs a conductor to dispatch it and a resume loop to return to), and SK-060's packaging (the layout decided here is the one the marketplace ships).
**Reference:** [backlog-01](backlog.md) — north star, invariants 3/5, findings F-1…F-5 · [design decisions](../../../.ai/reports/2026-07-12-supskill-design-decisions.md) — **D2** (skill = conductor UX, script = enforcement), **D6** (one sprint per invocation), **D7** (entry points) · [contexts/01](../../../.ai/reports/contexts/01-claude-code-context-mechanics.md) — `/clear` vs subagent vs compaction semantics · [contexts/02](../../../.ai/reports/contexts/02-skill-and-plugin-authoring.md) — plugin layout rules, frontmatter validation, the description regression.

## Sprint goal (one line)

> A `/supskill run <sprint-id>` skill inside a valid plugin skeleton that init's-or-resumes strictly from disk — invoke it mid-sprint after `/clear` and it reports the same stage, gates, and artifacts the dying context left behind, consulting nothing but `state.json`.

## Why this sprint

E1 built the spine; nothing invokes it yet. Every discipline the spine enforces is currently exercised by hand — the exact "lives in the operator's memory" failure supskill exists to close. E3–E6 all take the form "the conductor dispatches a stage subagent, records the artifact, holds a gate"; none of that has anywhere to live until the conductor exists.

This sprint is deliberately **thin and skeletal** (D2 splits the product in two, and the script half is done). The conductor gains stage implementations in E3–E6; here it only needs to do the three things the epic names: invoke, read state, resume. Two constraints dominate:

1. **The conductor is disposable** (invariant 5). Resume must be a pure function of `state.json` — the SKILL.md checklist may not depend on anything the previous context knew. contexts/01 §5 confirms `/clear` genuinely empties the window, which makes SK-012's test honest: whatever survives it, survived on disk.
2. **Invariant 3 grows a new surface.** Until now "the script is the only mutator of `state.json`" was a code-review check. From this sprint on it is also a **prose** check: SKILL.md must never instruct the model to edit `state.json`, and every mutation it choreographs must be a `supskill-state` call. The reviewer checks the skill body for this, and keeps checking on every future sprint.

One thing this sprint is **not**: the first stage. The temptation is to pull SK-020 (SCOPE dispatch) forward so the skeleton "does something." Resist it — E3 is the heart and deserves its own refinement pass and its own gate; a skeleton that init's, resumes, and honestly says "SCOPE is not implemented yet; here is the state" is the correct v-E2 behavior.

## Capacity & sequencing

Working capacity ~**34 pts**; ~18% buffer → ~**28 pts committable** (same model as S1). Committed: **12 pts** → single wave, large headroom — **deliberately unfilled**. E2 is thin by design; padding it with E3 stories would front-run a plan against a tree E2 is about to change (D6's staleness argument, applied to ourselves).

- **Critical path:** SK-010 (skeleton — decides the layout everything sits in) → SK-013 (entry point — the verb that makes the skill invocable) → SK-012 (resume — the behavior the verb must have on re-invoke).
- **SK-011 is independent** after SK-010 lands and may run in parallel with SK-012/SK-013.
- SK-012's CLI half (`show` growth) is pure Python and can land before its prose half; sequence the SKILL.md dispatch checklist after SK-013 so it documents the real matrix, not a guess.

## Stories

### SK-010 — Plugin skeleton · 2 · M

- **As** every component E3–E7 will ship, **I want** a valid plugin layout decided once, **so that** nothing built on it ever moves — the S1 scaffold explicitly promised room for this (`sprint-01` SK-007) and this story cashes that promise.

- **Context.** Design §6: `.claude-plugin/plugin.json`; components (`skills/`, `agents/`, `scripts/`) at plugin **root**, never inside `.claude-plugin/`. Two pull-time traps (DoR findings 3–4): the single-skill-at-plugin-root shorthand makes the invocation name drift with every marketplace update unless frontmatter `name` is set — sidestepped entirely by using a real `skills/` directory; and only `bin/` is auto-added to Bash `PATH`, `scripts/` is not — resolved by invoking the shim via `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, no PATH reliance, no `bin/`.

- **Accept:**
  - `.claude-plugin/plugin.json` with `name: supskill` (working title — the slug freeze is SK-060's decision; renaming costs nothing until first publish), `version`, `description`, `author`. Nothing else lives in `.claude-plugin/`.
  - `skills/supskill/SKILL.md` exists (placeholder until SK-011/SK-012 fill it) in a real `skills/` directory; `agents/` reserved for E3's stage agents. `scripts/` stays exactly where it is — `pyproject.toml`'s `pythonpath = ["scripts"]` and the shim's self-inserting `sys.path` (`scripts/supskill-state:7`) both keep working; `pytest` and `ruff` stay green, offline.
  - `claude plugin validate --strict` passes on the repo, and an offline test asserts the invariants a validator run can't be assumed for (plugin.json parses; `name` kebab-case, ≤64 chars, contains neither reserved word).
  - Invocation convention recorded in SKILL.md: the state CLI is always called as `${CLAUDE_PLUGIN_ROOT}/scripts/supskill-state`, from the **target repo's root** — `.supskill/` resolves from cwd (`store.py:26`), and nothing may persist under the plugin root (it is wiped on every update; contexts/02 §3).

### SK-011 — `SKILL.md` description: triggering conditions only · 3 · M

- **As** the discovery mechanism that decides whether this skill fires, **I want** a description that states only *when* to invoke and never *how* the workflow goes, **so that** the documented regression — a workflow-summarizing description causing agents to skip half the process — cannot happen here.

- **Context.** The regression is recorded in `superpowers:writing-skills` and quoted in design §6. The validation rules are hard numbers (contexts/02 §1): `name` ≤64 chars, lowercase+hyphens, no `anthropic`/`claude` substrings; `description` non-empty, ≤1024 chars, third person; combined `description` + `when_to_use` truncated at 1,536 rendered chars. One trap is silent: **malformed frontmatter YAML still loads the skill but with no description**, so it never auto-triggers and only `--debug` shows why. Pull-time decision (DoR finding 5): the conductor is side-effecting — it spawns subagents, spends tokens, mutates the operator's repo — so v1 is **user-invoked only** (`disable-model-invocation: true`), per contexts/02's own implication for side-effecting skills.

- **Accept:**
  - Frontmatter: explicit `name: supskill`, `argument-hint: run <sprint-id>`, `disable-model-invocation: true`, and a description that names triggering conditions (driving a sprint from a markdown backlog) and **contains no workflow summary** — no stage list, no gate list.
  - The invocation-model decision and its rationale recorded in the doc the skill links (one hop, per contexts/02 §2) — including the flagged tension: SK-061's should-trigger evals mostly test a path v1 has disabled; E7 revisits.
  - An offline frontmatter lint test in the suite: parses the YAML (failing loudly on the silent-failure mode), asserts every hard limit above. This is the CI step contexts/02 "Implications" #1 asks for.
  - Body ≤500 lines, checklist-shaped, one reference-hop deep.

### SK-012 — Conductor resumes from `state.json` alone · 4 · M · **(3 → 4 at pull time)**

- **As** the disposable conductor, **I want** re-invocation to reconstruct everything from disk, **so that** `/clear` mid-sprint is a non-event. (Invariant 5 — the product's core promise.)

- **Context (why it grew — DoR finding 1).** The resume surface is incomplete: `render_show` (`commands.py:107-135`) prints stage, gates, task counts, and blockers — but **not `artifacts` and not `backlog`**. A conductor resuming at PLAN needs `artifacts.sprint_doc` to hand `writing-plans` its spec; one resuming at SCOPE needs `backlog`. S1's `artifact` verb records these; nothing reads them back out. Rather than teach the skill prose to parse `state.json` internals (couples prose to schema, rots silently), the CLI owns the read contract too.

- **Accept:**
  - `show` gains an `artifacts:` section and a `backlog:` line; `show --json` prints the full state as JSON (`state_to_dict` already exists — `model.py:248` — this is wiring, not modeling). Offline tests: `show --json` output round-trips against the state file; the text form includes every field the dispatch table consumes.
  - SKILL.md resume checklist: on invoke, run `show --json`; `stage` alone selects the next action from a dispatch table (SCOPE/REFINE/PLAN/EXECUTE/REVIEW — all honest stubs this sprint: report the stage, name the epic that implements it, stop). No memory of any prior conversation is consulted; a missing or unreadable `state.json` is reported verbatim and the conductor stops — it never silently re-inits.
  - The invariant-5 test, run by the operator and scripted as a checklist in the sprint scratch: init a sprint, `gate`/`advance` it to REFINE, `/clear`, `/supskill run <id>` — the conductor reports REFINE, the pending gate, and the recorded artifact paths. (`seam: app-level`, `provable: operator` — see the honest scope note.)
  - The reviewer confirms invariant 3's new prose surface: no line of SKILL.md instructs editing `state.json`; every mutation is a `supskill-state` call.

### SK-013 — `/supskill run <sprint-id>` entry point · 3 · M · **(2 → 3 at pull time)**

- **As** the operator starting or returning to a sprint, **I want** one verb that does the right thing whatever is on disk, **so that** "start" and "resume" need no separate ceremony. Honours `sprint.entry` ∈ `SCOPE|PLAN|EXECUTE` (**D7**).

- **Context (why it grew — DoR finding 2).** "Run" hides a three-way matrix the one-liner never spelled out, and one cell is dangerous: `init` refuses when state exists (`commands.py:55-61`) unless `--archive` is passed — and the conductor must **never pass `--archive` on its own**. Archiving a half-finished sprint is an operator decision; a conductor that auto-archives on an id mismatch destroys the resume promise from the other direction. Entry-point honoring, meanwhile, costs nothing new: `init --entry` already sets the stage (`cli.py:34`), and transition-attached preconditions (`transitions.py:1-8`) already make a PLAN- or EXECUTE-entry legal.

- **Accept:**
  - The matrix, exhaustively: **no state** → `init <sprint-id>` (entry default SCOPE; `--entry`, backlog, branch taken from the operator's invocation) then proceed per SK-012's dispatch. **State exists, same normalized id** (`scratch.py` normalization — `S2` and `s2` are the same sprint) → resume; no mutation. **State exists, different id** → refuse, show both ids, name `supskill-state init --archive` as the operator's way forward — and stop there.
  - An init'd `--entry PLAN` or `--entry EXECUTE` sprint starts at that stage and the dispatch table lands on it directly — asserted by walking the matrix against a real `.supskill/` in a temp dir for every CLI-reachable cell.
  - `$ARGUMENTS` parsing documented in the skill body; a bare `/supskill run` (no id) with no state on disk asks nothing and reports usage — subagents can't ask, and the conductor should not build a habit the stages can't share.

## DoR findings (refined at pull time)

E2 is the first sprint refined against **live source** — S1's suite, CLI, and the two authoring reports. Sprint goes **10 → 12 pts** (SK-012 3 → 4, SK-013 2 → 3), far under the 28-pt guardrail.

1. **`show` is not a complete resume surface** (grew SK-012 3 → 4). `render_show` (`commands.py:107-135`) omits `artifacts` and `backlog` — precisely the fields a resuming conductor needs to hand the next stage its inputs. S1 added the `artifact` verb as a plan-time discovery (commit `9faa617`); the read side never caught up. Resolution: `show` grows the fields plus a `--json` mode, so the resume contract lives in the CLI, not in skill prose that parses schema internals.

2. **"Run" is a three-way matrix, and one cell must refuse** (grew SK-013 2 → 3). `init` refuses over existing state without `--archive` (`commands.py:55-61`) — correct, and the conductor must inherit the refusal rather than the flag. Auto-archiving on id mismatch would let a drifting model bury a half-finished sprint; the conductor names the flag and stops. Also resolved here: id comparison uses `normalize_sprint_id`, so case variants resume instead of colliding.

3. **The single-skill-at-root naming trap** (shapes SK-010). contexts/02 §3: with no `skills/` directory, a root `SKILL.md`'s invocation name falls back to the install directory — "a version string that changes on every update." A real `skills/supskill/SKILL.md` plus explicit frontmatter `name` closes both the trap and the ambiguity. Bonus: `plugin.json`'s `name` is only immutable **after** first publish; using the working title now costs nothing (SK-060 still owns the freeze).

4. **Only `bin/` joins `PATH`; `scripts/` does not** (shapes SK-010). Design §6 names `scripts/` as a root component, but the plugins reference only auto-`PATH`s `bin/`. No layout change needed: the shim already self-bootstraps its import path (`scripts/supskill-state:7`), so the skill invokes it by `${CLAUDE_PLUGIN_ROOT}` absolute path. Corollary made explicit: `.supskill/` resolves from **cwd** (`store.py:26`), so the convention "run from the target repo root" is stated in SKILL.md, and nothing ever persists under the plugin root (wiped on update).

5. **The conductor is side-effecting, so v1 is user-invoked only** (shapes SK-011). contexts/02's own implication #2: skills with side effects users should control the timing of get `disable-model-invocation: true`. Trade-off flagged, not hidden: SK-061's should-trigger eval loop (E7) mostly exercises auto-invocation, which v1 disables — E7 decides whether to relax it with evidence in hand.

6. **Nothing can populate `tasks[]` — a hole in a different epic** (backlog delta 3, not this sprint's scope). `record_blocker` refuses a blocker whose task is not in `state.tasks` (`commands.py:226-228`), `init` writes `tasks: []`, and **no verb adds tasks**. E5 therefore cannot block, park, or map SDD statuses onto anything until the PLAN stage loads tasks from the dev plan into state. That is a missing story in E4 — proposed below rather than smuggled in here.

**Deliberately NOT in scope**, though tempting: any stage implementation (SK-020+ — E3 is the heart and gets its own sprint), `marketplace.json` and the slug freeze (SK-060), description trigger evals (SK-061), the tasks-loading verb (E4's, per finding 6), and any hook-based enforcement — the spine plus loud refusal is the designed ceiling (F-4); a `PreToolUse` guard is gold-plating the design already ruled against.

**Gate 1 data point #2** (open question §7.2): refinement against live source grew scope +2 pts and, more tellingly, found a load-bearing gap in a *different* epic (finding 6) that no one would have met until E5 failed against it. Second consecutive data point that the refine pass earns its keep.

## Skills for executors

Standing skills apply (author↔review separation, verify-before-claim, no self-approval, TDD, `karpathy-guidelines`, no AI attribution in commits). Domain additions:

- **SK-010** — `context7` for current plugin.json/frontmatter idioms rather than memory; contexts/02 is the local authority where they disagree with recollection.
- **SK-011** — `superpowers:writing-skills` **first**: it is the primary source for the description regression this story exists to avoid. The frontmatter lint test is TDD'd like any other code.
- **SK-012 / SK-013 (CLI half)** — `fullstack-dev-skills:python-pro` + `superpowers:test-driven-development`; the suite stays pure offline — no LLM, no subagent, no network anywhere in it.
- **SK-012 / SK-013 (prose half)** — `superpowers:writing-skills` for the body; degrees-of-freedom framing applies (exact CLI invocations = low freedom, "report and stop" judgment = prose).
- **Review pass** — `oh-my-claudecode:code-reviewer` → `oh-my-claudecode:verifier`. The reviewer's standing invariant-3 check **extends to prose**: no line of SKILL.md may instruct editing `state.json` by hand. This check repeats every sprint from now on.

## Risks & mitigations

| Risk | Owner | Trigger / signal | Mitigation |
|------|-------|------------------|------------|
| **Description drifts into a workflow summary** during some future edit, silently re-triggering the documented regression | executor (011) | a stage or gate name appears in the frontmatter description | Lint test asserts the hard limits now; the no-summary property is a named reviewer check (it is judgment, not regex — say so honestly). |
| **The conductor re-inits instead of resuming**, or auto-archives on an id mismatch | executor (013) | a fresh `state.json` where a mid-sprint one stood; an unexplained `archive-N/` | The matrix is exhaustive and asserted per cell; `--archive` is structurally absent from the conductor's vocabulary — it names the flag to the operator and stops. |
| **Resume quietly depends on conversation memory** and nobody notices until a real `/clear` | operator | the operator test reports a different stage than `show` does | The dispatch table's only input is `show --json`; the operator-run `/clear` test is an exit criterion, not a nice-to-have. |
| **Wrong cwd writes `.supskill/` into the wrong repo** | executor (012) | a stray `.supskill/` outside the target repo | Convention stated in SKILL.md; the failure mode is loud anyway (`show` errors with "run init first" — `store.py:43`) — do not build path-divination on top. |
| **Prompt-shaped acceptance criteria get certified by the agent that wrote them** (F-5, this sprint's flavor) | operator | SK-012/SK-013 marked done with only the CLI tests green | Seam classification is explicit: the `/clear` test and matrix walk-through are `provable: operator`; the sprint does not close on offline green alone. |
| Working-title `name` hardens into a de-facto slug before SK-060 decides | operator | docs/posts referencing `/supskill` accumulate | Accepted consciously: rename is free until first publish, and SK-060 is the named decision point. |

## Exit criteria

- [ ] **SK-010:** `claude plugin validate --strict` green; `skills/supskill/SKILL.md` in a real `skills/` dir; nothing but `plugin.json` in `.claude-plugin/`; `pytest` + `ruff` still green offline with the layout untouched where S1 put it.
- [ ] **SK-011:** frontmatter has explicit `name`, `argument-hint`, `disable-model-invocation: true`; description states triggering conditions only; the lint test enforces every hard limit and fails on malformed YAML; the invocation-model decision and its E7 tension are written down.
- [ ] **SK-012:** `show` prints `artifacts` + `backlog`; `show --json` round-trips against the state file; dispatch table covers all five stages with honest stubs; reviewer confirms invariant 3 holds in prose.
- [ ] **SK-013:** all three matrix cells asserted against a real temp-dir `.supskill/`; `--entry PLAN|EXECUTE` sprints land on their entry stage; id-mismatch refuses and names `--archive` without using it.
- [ ] Full suite still pure offline and fast; every story TDD'd with failing-test-first evidence in the sprint scratch.
- [ ] **The sprint demo (invariant 5 in anger):** in a scratch repo — `/supskill run s2` → conductor init's, reports SCOPE, says "SCOPE lands in E3," stops → operator runs `gate G1` + `advance` by hand → **`/clear`** → `/supskill run s2` → the conductor reports the post-advance stage, the recorded gate decision, and the artifact paths, having read nothing but disk. Then `/supskill run s99` → refusal that names both ids and the archive flag.

> **Honest scope note:** E2's proof is split across seams for the first time. The CLI half (`show` growth, the init matrix) is offline-provable and TDD'd like S1. The conductor's *behavior* — resuming correctly, refusing correctly, stopping at stubs — is prompt-shaped: the suite cannot execute SKILL.md, so those criteria are proven by the operator-run demo and re-proven for real when E3 gives the conductor its first stage to dispatch. Claiming otherwise would be exactly the self-certification F-5 warns about.

## Backlog deltas — proposed (not yet applied)

To be applied to [backlog.md](backlog.md) once the operator accepts this doc:

1. **SK-012 re-pointed 3 → 4:** `show` grows `artifacts` + `backlog` and a `--json` mode — the resume read-contract lives in the CLI, not in prose parsing `state.json` internals.
2. **SK-013 re-scoped and re-pointed 2 → 3:** the init-or-resume-or-refuse matrix made explicit; the conductor never passes `--archive` itself; normalized-id comparison.
3. **New story proposed for E4 (3 pts, suggested SK-033):** a `supskill-state` verb that loads `tasks[]` (id, seam, provable, status=PENDING) from the refined sprint doc / dev plan into state. Today nothing populates tasks (`init` writes `[]`) while `block` requires the task to exist (`commands.py:226-228`) — without this verb, E5 cannot block, park, or map a single SDD status. E4 is the stage where tasks become known, so it lands there.
4. **SK-011's note records the invocation-model decision:** v1 is user-invoked only (`disable-model-invocation: true`) because the conductor is side-effecting; E7's eval story (SK-061) inherits the flagged tension.
5. **E2 total 10 → 12; Summary table and 115-pt grand total updated accordingly.**
6. **Gate 1 data point #2 recorded (open question §7.2):** live-source refinement grew scope +2 pts and exposed a cross-epic gap (the missing tasks verb) that would otherwise have surfaced as an E5 failure. Two sprints, two data points, same direction.
