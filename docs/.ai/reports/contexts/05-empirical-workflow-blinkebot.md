---
title: Empirical workflow evidence from blinkebot (~10 runs of sprint-plan → writing-plans → subagent-driven-development)
date: 2026-07-12
---

Blinkebot (`/home/bessa/Documents/projetos/blinkebot`) is a real, ~10-sprint-deep run of the manual
3-stage pipeline this project wants to automate. This report mines what actually happened on disk —
file anatomy, naming, scratch-state collisions, git practice, and every documented mid-execution
replan — as grounding for the plugin design, not theory about how the pipeline "should" work.

## The pipeline as actually practiced

The loop, evidenced by file timestamps and content cross-references:

1. **`/pm-execution:sprint-plan`** (or equivalent) turns a backlog row into a sprint doc:
   `docs/plans/sprints/backlog-01/backlog.md` → `docs/plans/sprints/backlog-01/sprint-09-curated-freshness.md`.
2. **`/clear`** (implicit — the dev plan and sprint doc are written by different sessions; the dev
   plan restates context the sprint doc already had).
3. **`superpowers:writing-plans`** turns the sprint doc into a dev plan:
   `docs/superpowers/plans/2026-07-11-sprint-09-curated-freshness.md` (69,744 bytes vs. the sprint
   doc's 29,481 — the dev plan is TDD-task-granular, the sprint doc is story-granular).
4. **`/clear`** again.
5. **`superpowers:subagent-driven-development`** executes the plan, writing its ledger to
   `.superpowers/sdd/` (briefs, reports, reviews, a running `progress.md`), and lands work as commits
   on a sprint branch, merged to `main`.

This is not a one-off — it is visible **eleven times** in the sprint-doc/dev-plan pairing alone: S1,
S2, S2b, S3, plugin system (S4–S7), S2d, S2e, S2f, S9, S9a, S9b, S10 all have this doc pair (some of
the earliest ones, S1/S2/S2b, predate the `docs/superpowers/plans/` convention and instead have a
`Plan N` file directly under `docs/plans/sprints/backlog-01/` — see Naming conventions below).

## Artifact anatomy

**Backlog entry** (`backlog.md`, both `backlog-01/` and `backlog-02/`): a markdown table row —
`| ID | Story | Pts | Pri | Status | Depends |` — e.g. `| BLK-072 | Feed get_following into the
entity tracker... | 3 | M | ☑ | 065,009 |`. Point estimates are Fibonacci, priority is MoSCoW
(M/S/C/W), status is one of `☐ ◐ ☑ ⊘`. Sprints are grouped under `## SN · EN — Title` headers with a
**"Status update" banner** appended in-place when reality diverges from plan (e.g. the 2026-07-06 and
2026-07-09 banners in `backlog-01/backlog.md:33-53` recording the RSC-frontend pivot and the E2c
opening — these are literally pasted into the master backlog as dated retrospective notes, not a
separate changelog file).

**Sprint doc** (`sprint-NN-slug.md`) — anatomy, consistent across S2e/S9/S10:
- H1 title + a metadata line: Epic, Points (**and a delta**, e.g. "16 committed (was 10 — see DoR
  findings)"), Milestone, Depends-on, Reference (links to discovery docs / precedent sprints).
- `## Sprint goal (one line)` — a single blockquote sentence.
- `## Why this sprint` — 1-2 numbered facts pulled from the *current source*, with file:line
  citations (e.g. "`_build_opportunities` constructs `ScoreInput(..., tracked_refs=set())` —
  hardcoded empty (`cli.py:63`)").
- `## Capacity & sequencing` — working capacity (~34 pts), buffer (~18%), committable (~28 pts), a
  named **critical path**, and an explicit **barrier** ("BLK-078 lands before BLK-073 is wired").
- `## Stories` — one `### BLK-NNN — Title · Npts · Pri` per story, each with **As/I want/So that**,
  a **Context** paragraph citing exact file:line evidence, and an **Accept** checklist.
- `## DoR findings (refined at pull time)` — numbered list of things pull-time refinement against
  the *actual current code* changed from the backlog's one-liner, each tied to a points delta.
- `## Skills for executors` — per-story skill/agent assignments (domain skills layered on 10
  "standing skills" defined once in `backlog-01/README.md`).
- `## Risks & mitigations` — a table: Risk / Owner / Trigger-signal / Mitigation.
- `## Exit criteria` — a checkbox list, phrased as falsifiable assertions ("cap reached on day N →
  `RateLimitError`; clock advanced to day N+1 → admitted, counter restarts at 1").
- `## Backlog deltas — proposed (not yet applied)` — a numbered list of edits to make to
  `backlog.md` once the operator accepts the sprint doc. **This is the sanctioned mechanism for the
  sprint doc to talk back to the backlog** — the backlog is not edited directly during sprint planning.
- (Post-execution, appended in place) `## Security review` and `## Voyager-vs-DOM verdict` /
  `## Findings that contradict this sprint's plan` sections get bolted onto the END of the sprint doc
  after the sprint runs — e.g. `sprint-02e-engagement-context.md:185-281` — so the sprint doc becomes
  a append-only record of plan **and** outcome, not just plan.

**Dev plan** (`docs/superpowers/plans/YYYY-MM-DD-sprint-NN-slug.md`) — anatomy, from
`2026-07-12-sprint-09b-public-slug-identity.md`:
- H1 + a **Goal** paragraph, then a **Root cause** section (when the plan follows a live
  investigation) with a bolded claim and a pointer to a `.superpowers/sdd/live-capture/DISCOVERY-*.md`
  file.
- `## Global Constraints` — a **repeat** of the invariants relevant to this plan (read-only, no AI
  attribution, behavior-preservation exceptions **named explicitly by file:line**, challenge
  fail-safe, cap discipline) — i.e. the dev plan re-derives the constraints rather than just linking
  `AGENTS.md`, so an executor never has to cross-reference.
- `## File Structure` — a table: File / Responsibility / Task-number. This is the plan's map of
  which task touches which file, used later to detect merge collisions between parallel tasks.
- `## Task N — Title` sections, each with explicit **RED** (failing test code, verbatim, to paste)
  → **run it, confirm FAIL** → **GREEN** (the minimal implementation, verbatim) steps. This is much
  finer-grained than the sprint doc's story-level Accept criteria — a dev-plan Task is roughly
  "one commit."

The dev plan is 2-5x the byte size of its sprint doc (e.g. S2e: sprint doc 36 KB → dev plan 145 KB)
because it inlines literal code for every RED/GREEN step.

## Naming conventions (and their inconsistencies)

- **Sprint docs:** `sprint-NN[letter]-slug.md`, living **directly inside** the backlog directory
  (`docs/plans/sprints/backlog-01/sprint-09-curated-freshness.md`), no date prefix.
- **Dev plans:** `YYYY-MM-DD-sprint-NN[letter]-slug.md`, living **flat** in
  `docs/superpowers/plans/` (not split by backlog directory — `backlog-02`'s sprint-10 dev plan sits
  next to `backlog-01`'s sprint-09 dev plan with no subfolder distinction).
- **Inconsistency #1 — the earliest sprints skip the sprint-doc stage entirely.** S1
  (`sprint-01-foundation.md`) points straight at `../2026-07-03-blinkebot-01-foundation-slice.md` (no
  `YYYY-MM-DD-sprint-01-...` naming — it predates the dev-plan convention) as "Plan 1" with full
  task-level detail already inline. S2's camoufox pivot similarly has
  `2026-07-05-camoufox-provider-design.md` + `2026-07-05-camoufox-provider-plan.md` sitting in
  `backlog-01/` (not `docs/superpowers/plans/`) — a design-doc-then-plan pairing that predates and
  differs from the later `sprint-NN` naming.
- **Inconsistency #2 — a sprint that has a dev plan but no sprint doc.** `sprint-09b` has
  `docs/superpowers/plans/2026-07-12-sprint-09b-public-slug-identity.md` (a full dev plan, complete
  with Global Constraints and Task breakdown) but **`ls docs/plans/sprints/backlog-01/ | grep 09b`
  returns nothing** — no `sprint-09b-*.md` file exists. Verified directly on disk. S9b originated
  as a live root-cause investigation of S9a's BLK-079 blocker and went straight from a diagnosis
  document (`.superpowers/sdd/live-capture/DISCOVERY-e9a-entity.md`) to a dev plan, skipping the
  sprint-planning stage — the pipeline's stage 1 was elided when the trigger was a live bug, not a
  backlog pull.
- **Inconsistency #3 — letter suffixes are overloaded.** `2b` means "pivot / replacement epic"
  (E2b superseded E2's feed path). `2c`–`2f` mean "sub-epic of a restoration effort" (E2c has four
  sprints S2c/S2d/S2e/S2f). `9a`/`9b` mean "follow-up sprint discovered by the S9 whole-branch
  review" (not sub-epics of S9 — S9 itself shipped complete). The letter does not have one consistent
  semantic across the backlog; it is "the next thing that came up," disambiguated only by reading
  each sprint doc's "Depends on" line.
- **`backlog-01` vs `backlog-02` is a hard fork, not a continuation.** `backlog-02/backlog.md:4`
  states "Supersedes backlog-01" — it is a wholesale backlog rewrite (new north star, new epic IDs
  E10-E15, old epics E6/E7/E8 imported read-only as "parked side quests"), not an incremented sprint
  counter. The directory split itself (`backlog-01/`, `backlog-02/`) was created in the *current*
  session (both are `??` untracked at conversation start) as a retroactive reorganization of what was
  previously a flat `docs/plans/sprints/*.md` (now all `D` deleted in git status) — i.e. the operator
  restructured sprint-doc storage into per-epoch folders only after ~9 sprints had already
  accumulated flat.

## Scratch-state hazards (the sdd collision, verified)

`.superpowers/sdd/` is **entirely git-ignored**: `.superpowers/sdd/.gitignore` contains a bare `*`
(confirmed: `git status --ignored` lists every file under it as Ignored; `git ls-files .superpowers`
returns nothing; `git log --all -- .superpowers` returns nothing — it has never been committed, ever).
It is pure local scratch state, invisible to any reviewer looking only at commits/PRs.

**The collision, exactly as memory `sdd-scratch-dir-collides-across-sprints` states, verified on
disk.** For sprints S2 (Camoufox), S2d, S2e, and S2f, every task's brief/report/review was written
directly into `.superpowers/sdd/task-N-{brief,report,review}.md` with **no sprint qualifier** —
`ls .superpowers/sdd/` shows `task-1-report.md` through `task-20-report.md` flat in the directory,
plus files like `task-9-security-review.md`, `task-11c-report.md`. Since each sprint's task numbering
restarts at 1, **a later sprint's Task 1 write silently overwrites (or, if read first, silently
misreads) an earlier sprint's Task 1 file** — there is nothing in the filename to distinguish "S2's
task-1-report.md" from "S2f's task-1-report.md." The top-level `progress.md` ledger has the same
problem: it is a single file per session, so each sprint's controller had to manually rename the
prior sprint's ledger before starting — evidenced by five archived snapshots sitting next to the
live one: `progress-sprint02-archived.md`, `progress-sprint02d-archived.md`,
`progress-sprint02e-archived.md`, `progress-sprint02f-archived.md`, `progress-sprint09-archived.md`.
That renaming is a **manual, easy-to-forget step** — nothing enforces it; it is pure operator/
controller discipline.

**The fix, self-applied starting at S9.** From S9 onward, every sprint's controller creates its own
subdirectory — `.superpowers/sdd/s9/`, `s2d/`, `s2e/`, `s2f/`, `s9a/`, `s9b/`, `s10/` — and every one
of their `progress.md` files contains the **identical boilerplate paragraph**, e.g. verbatim from
`s10/progress.md`:

> ## Workspace convention (avoids the known cross-sprint collision — `[[sdd-scratch-dir-collides-across-sprints]]`)
> All S10 briefs / reports / review packages live under `.superpowers/sdd/s10/`, NOT in
> `.superpowers/sdd/` directly — that directory holds Sprints 2/2d/2e/2f `task-N-*.md` files and a
> bare `task-1-report.md` would silently read as a prior sprint's. Pass the explicit OUTFILE argument
> to `task-brief` / `review-package`.

This is a **memory-driven, self-correcting convention** — the controller session that wrote S9's plan
apparently recorded the hazard as a persistent memory (the same `[[sdd-scratch-dir-collides-across-sprints]]`
tag used in this operator's own Claude memory file), and every subsequent sprint's controller
re-reads and re-applies it by copying the same paragraph into its own ledger. **It is not
tool-enforced** — nothing prevents a controller from forgetting to pass the `OUTFILE` argument and
writing flat again; it is a convention carried entirely in natural-language memory across sessions.
This is exactly the kind of gate a plugin should make structural (a scratch-dir path derived
automatically from the sprint ID) rather than relying on the agent remembering a past incident.

## Git practice

- **Branch-per-sprint, merged back to `main`.** `git branch -a` shows `sprint-02-camoufox-provider`,
  `sprint-03-v1-hardening`, `sprint-04-plugin-system`, `sprint-05-memory-plus`, `sprint-06-research`,
  `sprint-07-factcheck`, `feat/s2e-engagement-context`, `fix/camoufox-session-rotation`, and the
  current `feat/e10-alerting-spine` (the repo's checked-out HEAD is *not* `main` — it is mid-sprint
  on a feature branch, contradicting the environment's stale snapshot of "Current branch: main").
  Merges land as `Merge sprintNN: ...` commits (e.g. `9599af5 Merge sprint-04: pluggy plugin system
  (BLK-034..038)`, `4a929f9 Merge sprint-05: memory-plus feature plugin (BLK-039..042)`,
  `bf9d5e6 Merge sprint-07: advisory cited factcheck plugin (BLK-047..050)`).
- **One conventional-commit per task/story**, prefixed `feat|fix|test|docs|refactor|style|chore`,
  scoped `(area)`, frequently suffixed with the `BLK-NNN` id: e.g. `a1e7afe feat(camoufox): rewire
  read_entity_posts to rendered DOM + graceful degrade (BLK-066)`. No commit in the sampled ~150-line
  log carries any AI/Claude/Anthropic attribution — the standing rule holds in practice, not just on
  paper.
- **Path-scoped commits, explicitly.** Sprint ledgers repeatedly instruct: "Every commit must be
  PATH-SCOPED to the files that task's plan step names. Never `git add -A`" (`s9a/progress.md`,
  `s10/progress.md`) — because pre-existing uncommitted doc reorganizations (the backlog-01/
  backlog-02 split, deleted old sprint docs) sit in the working tree across multiple sprint branches
  and must not be swept into an unrelated task's commit. This is memory
  `dont-sweep-uncommitted-doc-edits-into-task-commits`, applied live and cited by name in the
  ledgers.
- **In-sprint fix commits, not reverts.** No `git revert` appears in the sampled log. Instead,
  mistakes are corrected forward within the same sprint: e.g. `faee868 fix(session): normalize
  JSESSIONID quotes; dotenv strips them (BLK-071)` followed later the same sprint by `0fedc3e
  fix(session): redact every JSESSIONID form; test the real redaction path (BLK-071)` — the second
  commit hardens the first's incomplete fix, discovered by the review pass, not by a later bug report.
- **In-flight controller/reviewer adjudication is recorded, not silently resolved.** `s9b/progress.md`
  documents a reviewer catching two IMPORTANT defects in the *plan's own prescribed code* (not an
  implementer deviation) mid-sprint, ruling them "fixed, not escalated to the operator" because they
  didn't contradict the plan's intent — and separately, a controller catching an implementer who
  edited a **third** test file against a plan constraint worded "exactly TWO sanctioned test edits,"
  ruling the edit itself correct but noting "flag-and-PAUSE, not flag-and-proceed, is the correct
  move on a constraint worded 'exactly'." These are exactly the kind of judgment calls a replan/
  adjust/defer gate needs to route: some deviations get silently corrected in-sprint, some get a
  paper-trail note, and — per S9b below — some get escalated all the way to the operator.

## Evidence of replanning/deferral in the wild

**Pattern 1 — "DoR findings refined at pull time" is an institutionalized, expected replan, not an
exception.** `backlog-01/README.md:97-108` (Definition of Ready) states explicitly: "Stories that
fail DoR are marked ⊘ and refined before commitment (the E2c read-surface stories S2d–S2f and the E9
payoff stories are intentionally coarse until their prior surface lands — refine them at pull time
against the captured fixture...)." This is not a failure mode the process tolerates — it is
*designed in*: every sprint doc examined (S2e, S9, S10) carries a "DoR findings (refined at pull
time)" section that grows the committed points versus the backlog's one-line estimate (S2e: 10→16,
S9: 14→16, S10: 18→23) because refining against the *actual current source* (not the backlog's
one-liner) surfaced load-bearing gaps the backlog couldn't have known about. A replan/adjust gate
needs a **first-class "refine at pull time" step**, not just an escape hatch for when things go wrong.

**Pattern 2 — E2 → E2b: a full pivot triggered by live discovery.** S2 (Camoufox + Voyager
interception) shipped and was reviewed, then a live run proved LinkedIn had migrated to a new React
Server Components frontend that the Voyager XHR-drain approach cannot see at all
(`backlog-01/backlog.md:33-41`, the "2026-07-06" status banner). The response was not a bugfix sprint
— it was a **new epic** (E2b) built on a from-scratch discovery/design/plan/build cycle
(`2026-07-05-camoufox-provider-design.md` was actually the *pre-pivot* design; the pivot got its own
`2026-07-06-e2b-rendered-dom-feed-design.md` + `-plan.md`), while explicitly marking the six other S2
read surfaces `☑⊘` ("built + reviewed, but obsoleted") rather than deleting or silently forgetting
them — they became E2c's backlog (S2c–S2f), resumed three sprints later.

**Pattern 3 — S9 → S9a: a whole-branch review turns "done" into a new sprint.** S9 shipped (merged
`b4ad2ec`, 410 tests green, one successful operator-gated live poll) and was marked ☑ in the backlog.
But its own **whole-branch review** — a *separate* review pass after all of S9's tasks individually
passed — found five mechanisms that were "built" in the sense of passing tests but had **zero
production callers**: reciprocity ingestion, the recurring poll scheduler, `serve`'s poll-provider
wiring, a dead config setting, and (a "C0, LIVE BLOCKER, highest priority" finding) the entity-page
parser silently returning 0 posts on every one of 23 live profile reads despite a clean,
challenge-free drive. These were recorded directly in the backlog under a **new heading** ("S9
follow-ups — runtime-wiring gaps surfaced by the whole-branch review (mechanism built, invocation
deferred)") with the explicit note "Assign BLK-IDs as you see fit" — i.e. the whole-branch reviewer
does not silently patch these in; it writes them back to the backlog as new, unscoped backlog items,
and a **new sprint-planning pass** (S9a, 13 pts, its own sprint doc + dev plan + SDD ledger) picks
them up. **This is the single clearest "whole-branch-review-becomes-a-new-sprint" data point in the
whole repo** — the review gate did not just gate merge, it generated the next sprint's backlog.

**Pattern 4 — S9a → S9b: a live investigation overturns the sprint's own diagnosis mid-flight.**
S9a's BLK-079 was scoped as "re-anchor the entity-page DOM parser — it must have drifted" (the
default assumption, since every other rendered-DOM surface had drifted at least once). The story was
explicitly gated: "Controller does NOT drive LinkedIn live... STOPS at BLK-079 Step 1 and hands off"
— an **autonomous execution boundary**, not a soft suggestion: everything offline-provable in S9a
(BLK-080/081/082/083) ran to completion unattended; the one story needing a live capture hard-stopped
and waited for the operator. When the operator-gated live capture happened, the root cause turned out
to be **not a parser drift at all**: `entity_posts_url` was building the profile URL from the opaque
`fsd_profile` id, and LinkedIn's own redirect from opaque-id → public-slug **discards the
`/recent-activity/all/` sub-path**, so every poll fetched a profile *root* (515k chars, 0 posts) and
the drift detector's heuristic ("big DOM, 0 posts") correctly but *misleadingly* fired "SELECTOR
DRIFT." The fix (`s9b/progress.md`) is documented as "**Operator rulings (locked before Task 1)**":
"1. Implement now, full planning + TDD + reviews (not a backlog item, not a quick patch). 2. One-shot
backfill: a single `curate` run resolves ALL missing slugs..." — i.e. the operator was consulted and
made an explicit process-shape decision (full sprint treatment, not a quick patch) **before any code
was written**, and the branch itself was renamed mid-flight from `fix/blk-079-entity-reanchor` to
`feat/e9b-public-slug-identity` to reflect the corrected diagnosis. This is the report's second
required focus point: **the 09/09a/09b sequence is not a linear breakdown of one estimate into three
— it is (a) ship, (b) review surfaces deferred wiring as a new sprint, (c) executing that sprint's
live-gated story disproves its own working diagnosis and forks into a differently-scoped sprint,
with an explicit operator go/no-go on process weight before it starts.**

**Pattern 5 — backlog-01 → backlog-02: a north-star reset.** Distinct from all of the above, S10's
predecessor event is not a sprint-review finding but an **operator-authored product pivot**:
`backlog-02/backlog.md:8-14` opens with "North star (operator's words, 2026-07-12)" — a verbatim
quoted paragraph reframing the whole product from a dashboard-you-check to an alert-that-pushes. This
triggered a wholesale backlog rewrite (new epics E10–E15), a formal "Inviolable invariants (locked)"
section restating read-only-forever with "Operator ruled this inviolable (2026-07-12)," and the
explicit demotion of three previously-live epics (research/factcheck/MCP) to "parked side quests...
off the critical path." A replan/adjust/defer gate must distinguish this shape of replan (operator-
initiated, backlog-wide, supersedes rather than amends) from Patterns 2-4 (execution-discovered,
scoped to one epic or sprint, amends in place).

**Deferrals tracked as first-class backlog state, not lost.** BLK-059 (narrow `AppContext` for
plugins) and BLK-060 (plugin dashboard-panel hookspec) were both explicitly deferred at S4's/S5's
gate with an operator-accepted rationale recorded inline in the backlog ("Fast-follow (deferred,
operator-accepted at S4 gate...)"), and BLK-060 is referenced and re-resolved ("not landed → BLK-075
adds a first-party route directly") three sprints later in S9's DoR findings — i.e. a deferred item
is a live dependency other sprints must re-check, not a closed loop.

## Project invariants the executor must respect

From `AGENTS.md` (the file every dev plan re-derives its own "Global Constraints" section from):

1. **Read-only, forever**, with exactly one narrowly-scoped, heavily-gated exception (a single
   bounded reactor-dialog click, scoped by selector + `aria-label` regex, asserted by a dedicated
   test that no write-capable control is reachable). Two standing test gates
   (`test_no_ui_affordance_writes_to_linkedin`, `test_client_fetch_calls_only_hit_internal_api`)
   enforce this on every template/route, including plugin-contributed ones.
2. **Provider abstraction is inviolable** — only `src/blinkebot/linkedin/` may import a
   browser/provider SDK; `codegraph_impact` is the sanctioned way to prove a change (e.g. a plugin)
   doesn't cross this boundary.
3. **Credentials are secrets** — redaction is attached to log **handlers**, not loggers (a
   documented gotcha: a filter on the logger itself doesn't scrub child-logger records). New
   credential classes (e.g. S10's SMTP password) must register with the same redaction filter or they
   leak in the first stack trace — caught proactively as a DoR finding, not after an incident.
4. **Challenge fail-safe, never retried** — a `ProviderChallenge` aborts the batch/poll entirely;
   adding a retry requires a scoped `security-reviewer` sign-off that has never been granted.
5. **Semantic anchors only** (`componentkey`/`aria`/URNs) — never hashed CSS classes, because
   LinkedIn's frontend re-serializes them; this is the standing mitigation for the recurring
   "selector drift" failure mode (S9a's BLK-079, ultimately a red herring, but the drift-detector
   heuristic and mitigation strategy are otherwise sound and reused every time a surface re-anchors).
6. **No AI attribution in git** — repo-wide and confirmed empirically clean across ~150 sampled
   commits.
7. Tooling: `uv run pytest -q` / `uv run ruff check` / Python ≥3.12; **offline suite only**, live
   paths gated behind `BLINKEBOT_LIVE_TEST=1` and never in the default suite.
8. **`codegraph` MCP is the sanctioned first move** for any "how does X work" / impact question —
   both `AGENTS.md` and every sprint doc's skills list route architecture questions there before
   grep/read.

## Requirements this evidence imposes on supskill

- **A structural (not memory-carried) scratch-dir namespace per sprint.** The sdd collision was only
  fixed because a controller happened to remember a prior incident and re-derive the same
  `.superpowers/sdd/<sprint-id>/` convention by hand, seven sprints in a row, verbatim. A plugin
  automating this pipeline should derive the scratch path from the sprint/plan identity automatically
  — this class of bug should be structurally impossible, not conventionally avoided.
- **A first-class "refine at pull time" step**, not just a failure-mode gate. Every sprint doc
  sampled grew its committed points from the backlog's estimate after refining against live code —
  this is the *normal* path, not the exceptional one. The replan/adjust gate should expect and budget
  for this on essentially every sprint, with the sprint doc's own "DoR findings" section as the
  template for what "refined" evidence looks like (file:line citations against current source).
- **A whole-branch-review-generates-next-backlog mechanism.** S9→S9a shows the review gate's output
  is not binary (approve/reject) — a review can surface N follow-up items that get written back to
  the backlog as new unscoped stories and picked up by the *next* planning pass. The plugin needs a
  path from "review found deferred-invocation gaps" to "backlog gains new rows," distinct from
  "review found a bug, fix it now."
- **A hard autonomous-execution boundary for live/operator-gated work**, with everything
  offline-provable running to completion first. S9a's controller ran four of five stories to green
  unattended and stopped cleanly at the one requiring a live LinkedIn capture, handing off explicitly
  rather than guessing. The gate must support "execute everything that doesn't need the operator, then
  stop and ask" as a normal sprint shape, not an error state.
- **A live diagnosis can invalidate its own sprint's scope mid-flight — support the fork, including a
  branch rename and an operator go/no-go on process weight**, without treating this as an aborted or
  failed sprint. S9b is not a "S9a went wrong" story; it is a correctly-functioning gate at a smaller
  granularity than sprint-level (task-level evidence overturning a task-level hypothesis, escalated
  for a scope decision, then executed with full rigor).
- **Distinguish backlog-amending replans from backlog-superseding resets.** Patterns 2-4 amend an
  existing backlog in place (status banners, new backlog-01 rows/sub-epics). Pattern 5 supersedes the
  whole backlog on an operator-authored north-star change. These need different gate treatments — the
  former can plausibly be semi-automated; the latter is inherently a full-stop, operator-only event
  (recorded here as a quoted operator statement + a "locked" invariants section) that a plugin should
  detect and hand off entirely, not try to merge into the running backlog.
- **Naming should tolerate stage-skipping without breaking traceability.** S1/S2 (pre-convention) and
  S9b (diagnosis-to-plan, no sprint doc) both show the 3-stage pipeline is sometimes legitimately
  2-stage in practice (a live investigation document standing in for the sprint doc). The plugin's
  naming/linking scheme should degrade gracefully — link a dev plan to its predecessor artifact
  (whichever stage produced it) rather than assuming a sprint doc always exists.
